"""
Automation Decision and Escalation Gatekeeper module.
Evaluates confidence, sentiment, urgency, intent complexity, and grounding
to decide whether an inbound customer conversation can be safely automated
or must be escalated to a human agent, providing transparent, audit-ready reasoning.
"""

import logging
from typing import List

from src.models import (
    AutomationDecision,
    AutomationGateResult,
    IntentCategory,
    SentimentLevel,
    UrgencyLevel,
    IntentClassificationResult,
    GroundedResponseResult,
    PreprocessedTweet
)
from src.config import settings

logger = logging.getLogger(__name__)


class AutomationGatekeeper:
    def __init__(self, confidence_threshold: float = None, similarity_threshold: float = None):
        self.confidence_threshold = confidence_threshold or settings.confidence_threshold
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold

    def evaluate(
        self,
        preprocessed: PreprocessedTweet,
        intent_result: IntentClassificationResult,
        grounded_response: GroundedResponseResult
    ) -> AutomationGateResult:
        """
        Multi-factor risk evaluation deciding between AUTOMATE and ESCALATE_TO_HUMAN.
        """
        risk_factors: List[str] = []
        decision = AutomationDecision.AUTOMATE
        routing_team = "Tier 1 Automated Fast-Path"
        reasoning_points: List[str] = []

        # 1. PII Safety Check
        if preprocessed.contains_masked_pii:
            risk_factors.append("Customer publicly shared sensitive PII (card, phone, or email).")
            decision = AutomationDecision.ESCALATE_TO_HUMAN
            routing_team = "Privacy & Data Protection Specialist"
            reasoning_points.append("Sensitive PII detected in public tweet; requires secure manual DM handling.")

        # 2. Critical Urgency / Extreme Sentiment Check
        if intent_result.sentiment == SentimentLevel.SEVERELY_DISSATISFIED or intent_result.urgency == UrgencyLevel.CRITICAL:
            risk_factors.append("Extreme customer dissatisfaction or critical crisis urgency.")
            decision = AutomationDecision.ESCALATE_TO_HUMAN
            routing_team = "Executive Escalations & Crisis Response Team"
            reasoning_points.append("Customer is severely dissatisfied or in critical distress; automated reply poses PR and churn risk.")

        # 3. High-Risk Intent Policies
        if intent_result.primary_intent == IntentCategory.COMPLAINT_FEEDBACK_ESCALATION:
            risk_factors.append("Intent is classified as an explicit complaint or escalation.")
            decision = AutomationDecision.ESCALATE_TO_HUMAN
            routing_team = "Senior Customer Experience Supervisor"
            reasoning_points.append("Direct complaints and legal/service escalations require empathetic human de-escalation.")

        elif intent_result.primary_intent == IntentCategory.ACCOUNT_SECURITY_ACCESS:
            risk_factors.append("Account security, password lockout, or unauthorized access.")
            decision = AutomationDecision.ESCALATE_TO_HUMAN
            routing_team = "Account Security & Fraud Prevention"
            reasoning_points.append("Account security actions require manual verification to prevent account takeover.")

        elif intent_result.primary_intent == IntentCategory.BILLING_REFUND_INQUIRY:
            # If refund/billing has high urgency or negative sentiment, escalate
            if intent_result.urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL] or intent_result.sentiment == SentimentLevel.NEGATIVE:
                risk_factors.append("Disputed charge or urgent refund inquiry.")
                decision = AutomationDecision.ESCALATE_TO_HUMAN
                routing_team = "Billing & Financial Operations"
                reasoning_points.append("Financial transactions and disputed charges require authorized billing agent review.")

        # 4. Confidence & Grounding Verification
        top_similarity = 0.0
        if grounded_response.grounded_in_exemplars:
            top_similarity = grounded_response.grounded_in_exemplars[0].similarity_score or 0.0

        if intent_result.confidence < self.confidence_threshold:
            risk_factors.append(f"Classification confidence ({intent_result.confidence:.2f}) below safety threshold ({self.confidence_threshold:.2f}).")
            if decision == AutomationDecision.AUTOMATE:
                decision = AutomationDecision.ESCALATE_TO_HUMAN
                routing_team = "General Support Queue (Tier 2 Review)"
                reasoning_points.append(f"Intent ambiguity detected (confidence: {intent_result.confidence:.2f}); routing to human for review.")

        if top_similarity < self.similarity_threshold and decision == AutomationDecision.AUTOMATE:
            risk_factors.append(f"Historical grounding similarity ({top_similarity:.2f}) is weak.")
            decision = AutomationDecision.ESCALATE_TO_HUMAN
            routing_team = "Subject Matter Expert Queue"
            reasoning_points.append("Query is novel or out-of-distribution with weak historical precedent.")

        # 5. Formulate Automation Rationale if Safe
        if decision == AutomationDecision.AUTOMATE:
            reasoning = (
                f"Safe for instant automation. High intent confidence ({intent_result.confidence:.2f}) "
                f"with strong historical grounding precedent (similarity: {top_similarity:.2f}). "
                f"Customer sentiment is {intent_result.sentiment.value} with no detected security, PII, or high-risk escalation flags."
            )
            gate_confidence = round(min(0.98, (intent_result.confidence + top_similarity) / 2.0), 2)
        else:
            reasoning = "Escalated to human agent: " + " ".join(reasoning_points)
            gate_confidence = round(max(0.85, intent_result.confidence), 2)

        return AutomationGateResult(
            decision=decision,
            confidence=gate_confidence,
            reasoning=reasoning,
            urgency=intent_result.urgency,
            routing_team=routing_team,
            risk_factors=risk_factors
        )
