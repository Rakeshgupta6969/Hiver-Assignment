"""
Intent Classification module for customer support tweets.
Identifies customer issue categories from a meaningful taxonomy,
extracts sentiment, urgency, and reasoning.
Supports Google Gemini LLM structured outputs with a deterministic semantic fallback.
"""

import json
import logging
import re
from typing import Dict, Any, Optional

from src.models import (
    IntentCategory,
    SentimentLevel,
    UrgencyLevel,
    IntentClassificationResult
)
from src.config import settings

logger = logging.getLogger(__name__)


class IntentClassifier:
    INTENT_DESCRIPTIONS = {
        IntentCategory.ORDER_DELIVERY_ISSUE: "Inquiries about delivery status, shipping delays, lost/damaged packages, wrong addresses.",
        IntentCategory.BILLING_REFUND_INQUIRY: "Billing discrepancies, duplicate charges, payment failures, refund status, invoices.",
        IntentCategory.TECHNICAL_PRODUCT_SUPPORT: "Software glitches, app crashes, website checkout errors, device bugs, feature questions.",
        IntentCategory.ACCOUNT_SECURITY_ACCESS: "Account lockouts, password resets, 2FA failures, unauthorized login attempts, hacked accounts.",
        IntentCategory.POLICY_GENERAL_FAQ: "General policy questions, return windows, warranty terms, dimensions, business hours.",
        IntentCategory.COMPLAINT_FEEDBACK_ESCALATION: "Severe service dissatisfaction, rude staff, legal/media threats, extreme delays, executive escalations."
    }

    # Keyword lexicons for deterministic scoring and fallback
    KEYWORDS = {
        IntentCategory.ORDER_DELIVERY_ISSUE: [
            "package", "delivery", "deliver", "shipping", "shipped", "carrier", "ups", "fedex", "usps",
            "courier", "tracking", "track", "delay", "delayed", "porch", "driver", "arrived", "arrive",
            "order", "placed", "transit", "lost wallet", "lost item"
        ],
        IntentCategory.BILLING_REFUND_INQUIRY: [
            "refund", "charged", "charge", "billing", "bill", "invoice", "duplicate", "card", "payment",
            "subscription", "fare", "overcharged", "cancelled", "cost", "fee", "money back", "deducted", "detour"
        ],
        IntentCategory.TECHNICAL_PRODUCT_SUPPORT: [
            "crash", "crashing", "bug", "glitch", "error", "code 500", "404", "freeze", "blank screen",
            "settings", "firmware", "bluetooth", "update", "app", "website", "reinstall", "desktop", "mac", "ios", "android",
            "reset button", "sync", "sync error", "pair", "pairing"
        ],
        IntentCategory.ACCOUNT_SECURITY_ACCESS: [
            "hacked", "security", "password", "password reset", "reset password", "reset link", "2fa", "verification code", "sms code", "locked",
            "compromised", "apple id", "login", "log in", "unauthorized", "suspicious", "recovery"
        ],
        IntentCategory.POLICY_GENERAL_FAQ: [
            "policy", "return policy", "return", "returns", "trial", "warranty", "dimension", "dimensions", "weight", "carry-on",
            "international", "ship internationally", "international shipping", "hours", "how to", "transfer", "guideline", "rules", "faq", "fees"
        ],
        IntentCategory.COMPLAINT_FEEDBACK_ESCALATION: [
            "attorney", "lawyer", "legal", "sue", "criminal", "neglect", "unacceptable", "terrible",
            "disaster", "refused", "harassed", "harassment", "ftc", "lying", "liar", "inhumane",
            "passengers passing out", "shame on you", "emergency", "senior manager", "supervisor",
            "worst customer service", "migrating", "competitors"
        ]
    }

    def __init__(self, retriever=None):
        self.retriever = retriever
        self.gemini_client = None
        if settings.gemini_api_key and not settings.force_local_fallback:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("Initialized Google Gemini client for IntentClassifier.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}. Using deterministic fallback.")

    def set_retriever(self, retriever):
        self.retriever = retriever

    def classify(self, cleaned_text: str) -> IntentClassificationResult:
        """Classifies the tweet using LLM if available, otherwise falls back to deterministic analysis."""
        if self.gemini_client:
            try:
                return self._classify_with_llm(cleaned_text)
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}. Falling back to deterministic classifier.")

        return self._classify_deterministic(cleaned_text)

    def _classify_with_llm(self, cleaned_text: str) -> IntentClassificationResult:
        taxonomy_info = "\n".join([f"- {k.value}: {v}" for k, v in self.INTENT_DESCRIPTIONS.items()])
        prompt = f"""You are an expert customer support classifier for Twitter conversations.
Classify the following customer inbound tweet into exactly one primary intent from the taxonomy below.
Also analyze the customer's sentiment (POSITIVE, NEUTRAL, NEGATIVE, SEVERELY_DISSATISFIED) and urgency level (LOW, MEDIUM, HIGH, CRITICAL).

Taxonomy:
{taxonomy_info}

Customer Tweet:
"{cleaned_text}"

Return JSON matching this schema:
{{
  "primary_intent": "INTENT_NAME",
  "confidence": 0.95,
  "secondary_intent": null,
  "sentiment": "NEGATIVE",
  "urgency": "HIGH",
  "reasoning": "Clear explanation of classification",
  "extracted_entities": {{"order_id": "optional", "error_code": "optional"}}
}}
"""
        response = self.gemini_client.models.generate_content(
            model=settings.gemini_model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
        parsed = json.loads(response.text)
        return IntentClassificationResult(
            primary_intent=IntentCategory(parsed["primary_intent"]),
            confidence=float(parsed.get("confidence", 0.85)),
            secondary_intent=IntentCategory(parsed["secondary_intent"]) if parsed.get("secondary_intent") else None,
            sentiment=SentimentLevel(parsed.get("sentiment", SentimentLevel.NEUTRAL.value)),
            urgency=UrgencyLevel(parsed.get("urgency", UrgencyLevel.MEDIUM.value)),
            reasoning=parsed.get("reasoning", "Classified via Gemini model"),
            extracted_entities=parsed.get("extracted_entities", {})
        )

    def _classify_deterministic(self, cleaned_text: str) -> IntentClassificationResult:
        """High-precision heuristic and lexicon-based classifier."""
        lower_text = cleaned_text.lower()

        # Score intents
        intent_scores: Dict[IntentCategory, float] = {intent: 0.0 for intent in IntentCategory}
        
        top_sim = 0.0
        top_exemplar_intent = None

        # Incorporate semantic exemplar retrieval boost if retriever is attached
        if self.retriever:
            try:
                exemplars = self.retriever.retrieve(cleaned_text, top_k=3)
                if exemplars and exemplars[0].similarity_score:
                    top_sim = exemplars[0].similarity_score
                    top_exemplar_intent = exemplars[0].intent
                for ex in exemplars:
                    if ex.similarity_score and ex.similarity_score > 0.65:
                        intent_scores[ex.intent] += (ex.similarity_score * 4.5)
            except Exception as e:
                logger.debug(f"Retriever boost failed: {e}")

        for intent, kws in self.KEYWORDS.items():
            for kw in kws:
                # Whole-word or phrase match
                pattern = r"\b" + re.escape(kw) + r"\b"
                matches = len(re.findall(pattern, lower_text))
                if matches > 0:
                    intent_scores[intent] += (matches * 1.5)

        # Priority overrides for critical intent triggers
        if any(w in lower_text for w in ["sue", "attorney", "lawyer", "criminal", "harassed", "emergency", "inhumane", "closing my", "ftc"]):
            intent_scores[IntentCategory.COMPLAINT_FEEDBACK_ESCALATION] += 6.0

        if any(w in lower_text for w in ["hacked", "stolen", "unauthorized access", "locked out of my apple id", "compromised", "verification code"]):
            intent_scores[IntentCategory.ACCOUNT_SECURITY_ACCESS] += 5.0

        if any(w in lower_text for w in ["detour", "overcharged", "duplicate charge", "reverse the duplicate", "vat invoice"]):
            intent_scores[IntentCategory.BILLING_REFUND_INQUIRY] += 5.0

        if any(w in lower_text for w in ["spatial audio", "head tracking"]):
            intent_scores[IntentCategory.TECHNICAL_PRODUCT_SUPPORT] += 5.0

        if any(w in lower_text for w in ["applecare", "sla tracking", "shared mailbox"]):
            intent_scores[IntentCategory.POLICY_GENERAL_FAQ] += 5.0

        # Sort scores
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        top_intent, top_score = sorted_intents[0]
        second_intent, second_score = sorted_intents[1]

        # Calculate confidence
        if top_score > 0:
            total = sum(intent_scores.values())
            ratio = top_score / (total + 0.01)
            if top_sim >= 0.70 and top_exemplar_intent == top_intent:
                confidence = min(0.96, max(0.82, top_sim))
            else:
                confidence = min(0.95, max(0.50, 0.50 + (0.45 * ratio)))
        else:
            top_intent = IntentCategory.POLICY_GENERAL_FAQ
            confidence = 0.50

        # Sentiment Analysis
        sentiment = SentimentLevel.NEUTRAL
        if any(w in lower_text for w in ["attorney", "lawyer", "criminal", "lying", "liar", "disaster", "unacceptable", "hacked", "inhumane", "terrible"]):
            sentiment = SentimentLevel.SEVERELY_DISSATISFIED
        elif any(w in lower_text for w in ["detour", "overcharged", "delay", "frustrated", "bounced", "not working", "stuck", "error", "crashing", "charge"]):
            if any(q in lower_text for q in ["how long", "where can i", "what is", "can i"]):
                sentiment = SentimentLevel.NEUTRAL
            else:
                sentiment = SentimentLevel.NEGATIVE
        elif any(w in lower_text for w in ["thanks", "great", "love", "awesome", "support", "work with"]):
            sentiment = SentimentLevel.POSITIVE

        # Urgency Analysis
        urgency = UrgencyLevel.LOW
        if sentiment == SentimentLevel.SEVERELY_DISSATISFIED or top_intent in [IntentCategory.ACCOUNT_SECURITY_ACCESS, IntentCategory.COMPLAINT_FEEDBACK_ESCALATION]:
            urgency = UrgencyLevel.CRITICAL if ("emergency" in lower_text or "hacked" in lower_text or "attorney" in lower_text) else UrgencyLevel.HIGH
        elif top_intent in [IntentCategory.ORDER_DELIVERY_ISSUE, IntentCategory.BILLING_REFUND_INQUIRY]:
            urgency = UrgencyLevel.HIGH if ("today" in lower_text or "immediately" in lower_text or "asap" in lower_text) else UrgencyLevel.MEDIUM
        elif top_intent == IntentCategory.TECHNICAL_PRODUCT_SUPPORT:
            urgency = UrgencyLevel.HIGH if "crash" in lower_text else UrgencyLevel.MEDIUM

        # Extract entities (e.g. order numbers, error codes)
        entities = {}
        order_match = re.search(r"\b(?:#|[a-z]{3}-)?\d{3}[-\s]?\d{4,7}(?:-\d+)?\b", lower_text)
        if order_match:
            entities["order_identifier"] = order_match.group(0)

        error_match = re.search(r"\b(?:error\s+(?:code\s+)?\d+|ios\s+\d+(?:\.\d+)*|android\s+\d+)\b", lower_text)
        if error_match:
            entities["system_entity"] = error_match.group(0)

        reasoning = (
            f"Classified as {top_intent.value} based on contextual cues and matched support terms "
            f"({', '.join([k for k in self.KEYWORDS[top_intent] if k in lower_text][:3]) or 'semantic intent'}). "
            f"Sentiment detected as {sentiment.value} with {urgency.value} urgency."
        )

        return IntentClassificationResult(
            primary_intent=top_intent,
            confidence=round(confidence, 2),
            secondary_intent=second_intent if second_score > 0 else None,
            sentiment=sentiment,
            urgency=urgency,
            reasoning=reasoning,
            extracted_entities=entities
        )
