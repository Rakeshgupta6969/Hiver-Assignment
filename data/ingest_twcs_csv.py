"""
Kaggle Twitter Customer Support Dataset (twcs.csv) Ingestion Pipeline.
Enables scaling the knowledge base from the demo subset to thousands/millions
of real customer-brand conversation pairs from Kaggle.

Usage:
    python data/ingest_twcs_csv.py --csv /path/to/twcs.csv --sample-per-brand 200
"""

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from src.knowledge_retriever import KnowledgeRetriever
from src.intent_classifier import IntentClassifier
from src.models import IntentCategory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("twcs_ingest")


def parse_twcs_csv(csv_path: Path, max_pairs: int = 1000) -> List[Dict[str, Any]]:
    """
    Parses Kaggle's twcs.csv to extract 1-to-1 conversation pairs:
    Customer Inbound Tweet -> Official Outbound Brand Reply.
    """
    logger.info(f"Opening {csv_path}...")
    
    # twcs.csv columns: tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id
    tweets_by_id = {}
    inbound_tweets = []

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            tweet_id = row["tweet_id"]
            tweets_by_id[tweet_id] = row
            if row["inbound"].lower() == "true" and row.get("response_tweet_id"):
                inbound_tweets.append(row)
            if i >= max_pairs * 5:  # buffer for pairing
                break

    logger.info(f"Loaded {len(tweets_by_id)} tweets. Pairing customer queries with brand replies...")

    paired_data = []
    classifier = IntentClassifier()

    for item in inbound_tweets:
        response_ids = item["response_tweet_id"].split(",")
        first_resp_id = response_ids[0].strip()

        if first_resp_id in tweets_by_id:
            brand_tweet = tweets_by_id[first_resp_id]
            customer_text = item["text"].strip()
            brand_reply = brand_tweet["text"].strip()
            brand_name = brand_tweet["author_id"]

            # Classify intent for indexing metadata
            intent_res = classifier.classify(customer_text)

            paired_data.append({
                "id": f"TWCS_{item['tweet_id']}",
                "brand": brand_name,
                "intent": intent_res.primary_intent.value,
                "customer_query": customer_text,
                "brand_response": brand_reply,
                "metadata": {
                    "sentiment": intent_res.sentiment.value,
                    "urgency": intent_res.urgency.value,
                    "source": "kaggle_twcs_csv"
                }
            })

            if len(paired_data) >= max_pairs:
                break

    logger.info(f"Successfully constructed {len(paired_data)} customer-brand conversation pairs.")
    return paired_data


def index_into_chroma(pairs: List[Dict[str, Any]]):
    """Indexes extracted pairs into the ChromaDB vector store."""
    retriever = KnowledgeRetriever()
    collection = retriever.collection

    batch_size = 100
    total = len(pairs)
    logger.info(f"Indexing {total} records into ChromaDB in batches of {batch_size}...")

    for i in range(0, total, batch_size):
        batch = pairs[i:i + batch_size]
        ids = [p["id"] for p in batch]
        documents = [p["customer_query"] for p in batch]
        metadatas = [{
            "brand": p["brand"],
            "intent": p["intent"],
            "brand_response": p["brand_response"],
            "sentiment": p.get("metadata", {}).get("sentiment", "NEUTRAL"),
            "resolution_type": "KAGGLE_TWCS"
        } for p in batch]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Indexed {min(i + batch_size, total)}/{total} documents.")

    logger.info(f"Indexing complete! Collection now has {collection.count()} exemplars.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Kaggle twcs.csv into ChromaDB")
    parser.add_argument("--csv", type=Path, default=Path("data/twcs.csv"), help="Path to twcs.csv")
    parser.add_argument("--max-pairs", type=int, default=500, help="Number of pairs to ingest")
    parser.add_argument("--export-json", type=Path, default=None, help="Optional path to save JSON")
    args = parser.parse_args()

    if not args.csv.exists():
        logger.error(f"File {args.csv} does not exist. Please download twcs.csv from Kaggle.")
    else:
        pairs = parse_twcs_csv(args.csv, max_pairs=args.max_pairs)
        if args.export_json:
            with open(args.export_json, "w", encoding="utf-8") as f:
                json.dump(pairs, f, indent=2)
            logger.info(f"Exported pairs to {args.export_json}")
        index_into_chroma(pairs)
