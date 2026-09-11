"""
Knowledge retrieval module using ChromaDB.
Indexes historical Twitter customer support pairs and retrieves the most relevant
exemplars to ground response generation in historical brand responses.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from src.models import HistoricalExemplar, IntentCategory
from src.config import settings

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    COLLECTION_NAME = "twitter_support_exemplars"

    def __init__(self, persist_dir: Optional[Path] = None, dataset_path: Optional[Path] = None):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.dataset_path = dataset_path or settings.dataset_path
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Persistent Chroma Client
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.seed_if_empty()

    def seed_if_empty(self) -> int:
        """Loads historical interactions into ChromaDB if the collection is empty."""
        current_count = self.collection.count()
        if current_count > 0:
            logger.info(f"Chroma collection already contains {current_count} documents.")
            return current_count

        if not self.dataset_path.exists():
            logger.warning(f"Dataset path {self.dataset_path} does not exist. Cannot seed.")
            return 0

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            interactions = json.load(f)

        ids = []
        documents = []
        metadatas = []

        for item in interactions:
            ids.append(item["id"])
            documents.append(item["customer_query"])
            metadatas.append({
                "brand": item["brand"],
                "intent": item["intent"],
                "brand_response": item["brand_response"],
                "sentiment": item.get("metadata", {}).get("sentiment", "NEUTRAL"),
                "resolution_type": item.get("metadata", {}).get("resolution_type", "GENERAL")
            })

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully seeded {len(ids)} historical interactions into ChromaDB.")
        return len(ids)

    def retrieve(
        self,
        query: str,
        intent_filter: Optional[IntentCategory] = None,
        top_k: int = 3
    ) -> List[HistoricalExemplar]:
        """
        Retrieves top_k most similar historical customer queries and their brand responses.
        Filters by intent if provided, falling back to general search if results are scarce.
        """
        where_clause = None
        if intent_filter:
            where_clause = {"intent": intent_filter.value}

        results = None
        try:
            if where_clause:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where_clause
                )
        except Exception as e:
            logger.warning(f"Filtered retrieval error: {e}, attempting unfiltered retrieval.")

        # Fallback to unfiltered query if filtered returned no documents
        if not results or not results["ids"] or len(results["ids"][0]) == 0:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

        exemplars: List[HistoricalExemplar] = []
        if not results or not results["ids"] or len(results["ids"][0]) == 0:
            return exemplars

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(ids)

        for i in range(len(ids)):
            meta = metas[i]
            # Convert cosine distance (0 to 2) into similarity score (0 to 1)
            dist = distances[i]
            similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            
            exemplars.append(
                HistoricalExemplar(
                    id=ids[i],
                    brand=meta.get("brand", "UnknownBrand"),
                    customer_query=docs[i],
                    brand_response=meta.get("brand_response", ""),
                    intent=IntentCategory(meta.get("intent", IntentCategory.POLICY_GENERAL_FAQ.value)),
                    similarity_score=round(similarity, 4)
                )
            )

        return exemplars
