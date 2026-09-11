"""
Unit tests for Grounded Response Generator.
"""

import pytest
from src.response_generator import ResponseGenerator
from src.intent_classifier import IntentClassifier
from src.knowledge_retriever import KnowledgeRetriever
from src.config import settings


@pytest.fixture(scope="module")
def pipeline_deps():
    return {
        "classifier": IntentClassifier(),
        "retriever": KnowledgeRetriever(),
        "generator": ResponseGenerator()
    }


def test_generated_reply_length_constraint(pipeline_deps):
    query = "My package was delayed by 3 days! Tracking is not updating."
    intent_res = pipeline_deps["classifier"].classify(query)
    exemplars = pipeline_deps["retriever"].retrieve(query, intent_res.primary_intent, top_k=3)
    response_res = pipeline_deps["generator"].generate_response(query, intent_res, exemplars, "AmazonHelp")

    assert len(response_res.generated_reply) <= settings.max_tweet_characters
    assert response_res.character_count <= settings.max_tweet_characters
    assert len(response_res.grounded_in_exemplars) > 0


def test_grounding_preserves_historical_resolution(pipeline_deps):
    query = "What are maximum carry-on bag dimensions for domestic flights?"
    intent_res = pipeline_deps["classifier"].classify(query)
    exemplars = pipeline_deps["retriever"].retrieve(query, intent_res.primary_intent, top_k=2)
    response_res = pipeline_deps["generator"].generate_response(query, intent_res, exemplars, "Delta")

    assert len(response_res.generated_reply) > 20
    # Must contain grounded guidance from historical resolution
    assert any(term in response_res.generated_reply.lower() for term in ["inches", "carry-on", "bag", "delta", "dimensions"])
