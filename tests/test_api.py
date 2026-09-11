"""
Integration tests for FastAPI REST endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["indexed_exemplars"] >= 20


def test_intents_endpoint():
    response = client.get("/api/intents")
    assert response.status_code == 200
    data = response.json()
    assert "intents" in data
    assert len(data["intents"]) == 6


def test_process_tweet_endpoint():
    payload = {
        "tweet_text": "@AmazonHelp My package #402-8921821 is delayed and tracking is stuck!",
        "brand_context": "AmazonHelp"
    }
    response = client.post("/api/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent_classification"]["primary_intent"] == "ORDER_DELIVERY_ISSUE"
    assert "generated_reply" in data["grounded_response"]
    assert data["automation_decision"]["decision"] in ["AUTOMATE", "ESCALATE_TO_HUMAN"]
    assert data["execution_time_ms"] > 0


def test_batch_process_endpoint():
    payload = [
        {"tweet_text": "What is the baggage limit on Delta?", "brand_context": "Delta"},
        {"tweet_text": "You charged me twice! Refund now!", "brand_context": "AmazonHelp"}
    ]
    response = client.post("/api/batch", json=payload)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["intent_classification"]["primary_intent"] == "POLICY_GENERAL_FAQ"
    assert results[1]["intent_classification"]["primary_intent"] == "BILLING_REFUND_INQUIRY"


def test_dashboard_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hiver" in response.text
