"""
Unit tests for Intent Classification taxonomy and analysis.
"""

import pytest
from src.intent_classifier import IntentClassifier
from src.models import IntentCategory, SentimentLevel, UrgencyLevel


@pytest.fixture
def classifier():
    return IntentClassifier()


def test_order_delivery_intent(classifier):
    text = "My package #402-8921821 is delayed and tracking is not updating"
    res = classifier.classify(text)
    assert res.primary_intent == IntentCategory.ORDER_DELIVERY_ISSUE
    assert res.confidence >= 0.70
    assert "402-8921821" in res.extracted_entities.get("order_identifier", "")


def test_billing_refund_intent(classifier):
    text = "I was charged twice $14.99 on my credit card. Reverse duplicate charge!"
    res = classifier.classify(text)
    assert res.primary_intent == IntentCategory.BILLING_REFUND_INQUIRY
    assert res.confidence >= 0.70


def test_technical_support_intent(classifier):
    text = "My app crashes with error code 500 on checkout page iOS 18"
    res = classifier.classify(text)
    assert res.primary_intent == IntentCategory.TECHNICAL_PRODUCT_SUPPORT
    assert res.confidence >= 0.70


def test_account_security_intent(classifier):
    text = "Someone hacked into my account and changed the password! Unauthorized access!"
    res = classifier.classify(text)
    assert res.primary_intent == IntentCategory.ACCOUNT_SECURITY_ACCESS
    assert res.urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]


def test_policy_faq_intent(classifier):
    text = "What is the return policy window for items purchased during holiday sale?"
    res = classifier.classify(text)
    assert res.primary_intent == IntentCategory.POLICY_GENERAL_FAQ


def test_complaint_escalation_intent(classifier):
    text = "Your representative was criminal and abusive! I am contacting my attorney to sue you in court!"
    res = classifier.classify(text)
    assert res.primary_intent == IntentCategory.COMPLAINT_FEEDBACK_ESCALATION
    assert res.sentiment == SentimentLevel.SEVERELY_DISSATISFIED
    assert res.urgency == UrgencyLevel.CRITICAL
