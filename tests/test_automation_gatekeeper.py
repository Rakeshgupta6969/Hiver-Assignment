"""
Unit tests for Automation Decision and Escalation Gatekeeper.
"""

import pytest
from src.automation_gatekeeper import AutomationGatekeeper
from src.preprocessor import TweetPreprocessor
from src.models import (
    AutomationDecision,
    IntentCategory,
    SentimentLevel,
    UrgencyLevel,
    IntentClassificationResult,
    GroundedResponseResult,
    HistoricalExemplar
)


@pytest.fixture
def gatekeeper():
    return AutomationGatekeeper()


@pytest.fixture
def preprocessor():
    return TweetPreprocessor()


def test_safe_inquiry_automated(gatekeeper, preprocessor):
    tweet = preprocessor.clean("Where can I find your return policy for international orders?")
    intent_res = IntentClassificationResult(
        primary_intent=IntentCategory.POLICY_GENERAL_FAQ,
        confidence=0.95,
        sentiment=SentimentLevel.NEUTRAL,
        urgency=UrgencyLevel.LOW,
        reasoning="Standard FAQ inquiry"
    )
    exemplar = HistoricalExemplar(
        id="1",
        brand="NikeSupport",
        customer_query="What is return policy?",
        brand_response="Our return policy is 60 days.",
        intent=IntentCategory.POLICY_GENERAL_FAQ,
        similarity_score=0.85
    )
    grounded_res = GroundedResponseResult(
        generated_reply="Our return policy is 60 days.",
        grounded_in_exemplars=[exemplar],
        character_count=30,
        direct_message_suggested=False,
        tone="Helpful"
    )

    decision = gatekeeper.evaluate(tweet, intent_res, grounded_res)
    assert decision.decision == AutomationDecision.AUTOMATE
    assert "Safe for instant automation" in decision.reasoning
    assert decision.routing_team == "Tier 1 Automated Fast-Path"


def test_legal_threat_escalated(gatekeeper, preprocessor):
    tweet = preprocessor.clean("You ruined my event! I am hiring a lawyer to sue you for damages!")
    intent_res = IntentClassificationResult(
        primary_intent=IntentCategory.COMPLAINT_FEEDBACK_ESCALATION,
        confidence=0.96,
        sentiment=SentimentLevel.SEVERELY_DISSATISFIED,
        urgency=UrgencyLevel.CRITICAL,
        reasoning="Severe dissatisfaction and legal threat"
    )
    grounded_res = GroundedResponseResult(
        generated_reply="We are escalating this to our senior management.",
        grounded_in_exemplars=[],
        character_count=50,
        direct_message_suggested=True,
        tone="De-escalating"
    )

    decision = gatekeeper.evaluate(tweet, intent_res, grounded_res)
    assert decision.decision == AutomationDecision.ESCALATE_TO_HUMAN
    assert any("dissatisfaction" in rf.lower() or "complaint" in rf.lower() for rf in decision.risk_factors)


def test_account_security_escalated(gatekeeper, preprocessor):
    tweet = preprocessor.clean("My account was hacked and I cannot reset my password!")
    intent_res = IntentClassificationResult(
        primary_intent=IntentCategory.ACCOUNT_SECURITY_ACCESS,
        confidence=0.92,
        sentiment=SentimentLevel.NEGATIVE,
        urgency=UrgencyLevel.HIGH,
        reasoning="Account compromised"
    )
    grounded_res = GroundedResponseResult(
        generated_reply="Please DM us to begin account recovery.",
        grounded_in_exemplars=[],
        character_count=40,
        direct_message_suggested=True,
        tone="Urgent"
    )

    decision = gatekeeper.evaluate(tweet, intent_res, grounded_res)
    assert decision.decision == AutomationDecision.ESCALATE_TO_HUMAN
    assert "Account Security" in decision.routing_team


def test_pii_leak_escalated(gatekeeper, preprocessor):
    # Accidental credit card leak in public tweet
    tweet = preprocessor.clean("Refund my card 4532-1122-3344-5566 immediately!")
    intent_res = IntentClassificationResult(
        primary_intent=IntentCategory.BILLING_REFUND_INQUIRY,
        confidence=0.85,
        sentiment=SentimentLevel.NEGATIVE,
        urgency=UrgencyLevel.HIGH,
        reasoning="Billing refund"
    )
    grounded_res = GroundedResponseResult(
        generated_reply="Please DM us your details.",
        grounded_in_exemplars=[],
        character_count=25,
        direct_message_suggested=True,
        tone="Professional"
    )

    decision = gatekeeper.evaluate(tweet, intent_res, grounded_res)
    assert decision.decision == AutomationDecision.ESCALATE_TO_HUMAN
    assert any("PII" in rf for rf in decision.risk_factors)
