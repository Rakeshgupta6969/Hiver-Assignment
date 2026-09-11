"""
Response Generation module for customer support tweets.
Generates helpful, brand-aligned replies strictly grounded in historical brand responses.
Adheres to Twitter's 280-character limit and privacy best practices.
"""

import json
import logging
from typing import List, Optional

from src.models import (
    IntentClassificationResult,
    HistoricalExemplar,
    GroundedResponseResult,
    IntentCategory
)
from src.config import settings

logger = logging.getLogger(__name__)


class ResponseGenerator:
    def __init__(self):
        self.gemini_client = None
        if settings.gemini_api_key and not settings.force_local_fallback:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("Initialized Google Gemini client for ResponseGenerator.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}. Using deterministic generation.")

    def generate_response(
        self,
        customer_query: str,
        intent_result: IntentClassificationResult,
        exemplars: List[HistoricalExemplar],
        brand_name: str = "Support"
    ) -> GroundedResponseResult:
        """
        Generates a grounded response using historical exemplars as factual precedent.
        """
        if self.gemini_client and exemplars:
            try:
                return self._generate_with_llm(customer_query, intent_result, exemplars, brand_name)
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}. Falling back to deterministic grounding.")

        return self._generate_deterministic(customer_query, intent_result, exemplars, brand_name)

    def _generate_with_llm(
        self,
        customer_query: str,
        intent_result: IntentClassificationResult,
        exemplars: List[HistoricalExemplar],
        brand_name: str
    ) -> GroundedResponseResult:
        grounding_context = "\n\n".join([
            f"Historical Query {i+1}: \"{ex.customer_query}\"\nHistorical Brand Reply {i+1}: \"{ex.brand_response}\""
            for i, ex in enumerate(exemplars[:3])
        ])

        prompt = f"""You are a professional customer support representative for @{brand_name} on Twitter.
Your goal is to reply to the customer's inbound tweet.

CRITICAL REQUIREMENTS:
1. Ground your answer STRICTLY in the historical brand responses below. Emulate their policy, tone, and action steps.
2. Max length: Under 280 characters.
3. If personal or account verification is needed, ask them to send a Direct Message (DM) with details.
4. Maintain empathy and professionalism.

Historical Brand Grounding Context:
{grounding_context}

Inbound Customer Tweet:
"{customer_query}"
Classified Intent: {intent_result.primary_intent.value}
Sentiment: {intent_result.sentiment.value}

Return JSON matching this schema:
{{
  "reply": "Your response under 280 characters",
  "tone": "Empathetic & Professional",
  "dm_suggested": true
}}
"""
        response = self.gemini_client.models.generate_content(
            model=settings.gemini_model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        parsed = json.loads(response.text)
        reply = parsed["reply"].strip()

        # Enforce 280 char limit safety
        if len(reply) > settings.max_tweet_characters:
            reply = reply[:settings.max_tweet_characters - 3] + "..."

        return GroundedResponseResult(
            generated_reply=reply,
            grounded_in_exemplars=exemplars,
            character_count=len(reply),
            direct_message_suggested=parsed.get("dm_suggested", "dm" in reply.lower()),
            tone=parsed.get("tone", "Empathetic & Solution-Oriented")
        )

    def _generate_deterministic(
        self,
        customer_query: str,
        intent_result: IntentClassificationResult,
        exemplars: List[HistoricalExemplar],
        brand_name: str
    ) -> GroundedResponseResult:
        """
        Synthesizes a response by directly grounding in the top historical brand exemplar.
        Adapts the exemplar's proven resolution SOP to the customer's context.
        """
        if exemplars and len(exemplars) > 0:
            top_exemplar = exemplars[0]
            base_response = top_exemplar.brand_response
        else:
            base_response = "We want to help resolve this for you right away. Please send us a DM with your details so we can investigate."

        # Adapt response if necessary to keep brand consistency and fit within 280 chars
        reply = base_response.strip()
        if len(reply) > settings.max_tweet_characters:
            reply = reply[:settings.max_tweet_characters - 3] + "..."

        dm_suggested = "dm" in reply.lower() or "direct message" in reply.lower()
        
        tone = "Empathetic & Direct"
        if intent_result.confidence > 0.8:
            tone = "Grounded & Authoritative"
        if intent_result.sentiment.value in ["NEGATIVE", "SEVERELY_DISSATISFIED"]:
            tone = "Empathetic & De-escalating"

        return GroundedResponseResult(
            generated_reply=reply,
            grounded_in_exemplars=exemplars,
            character_count=len(reply),
            direct_message_suggested=dm_suggested,
            tone=tone
        )
