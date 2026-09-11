"""
Unit tests for ChromaDB knowledge retrieval of historical brand exemplars.
"""

import pytest
from src.knowledge_retriever import KnowledgeRetriever
from src.models import IntentCategory


@pytest.fixture(scope="module")
def retriever():
    return KnowledgeRetriever()


def test_retriever_seeded(retriever):
    count = retriever.collection.count()
    assert count >= 20, f"Expected at least 20 historical documents, found {count}"


def test_retrieval_returns_exemplars(retriever):
    query = "Where is my package? It says delivered but it is missing."
    exemplars = retriever.retrieve(query=query, intent_filter=IntentCategory.ORDER_DELIVERY_ISSUE, top_k=3)
    assert len(exemplars) == 3
    for ex in exemplars:
        assert ex.intent == IntentCategory.ORDER_DELIVERY_ISSUE
        assert ex.brand_response
        assert ex.similarity_score is not None
        assert 0.0 <= ex.similarity_score <= 1.0


def test_unfiltered_retrieval_fallback(retriever):
    query = "Can you help me reset my password?"
    exemplars = retriever.retrieve(query=query, top_k=2)
    assert len(exemplars) == 2
    assert exemplars[0].similarity_score >= 0.5
