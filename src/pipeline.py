"""
End-to-end AI Customer Support Agent Pipeline.
Coordinates preprocessing, intent classification, grounding retrieval,
response generation, and automation gating.
"""

import time
import logging
from typing import List, Dict, Any, Optional

from src.models import (
    SupportAgentRequest,
    SupportAgentResponse,
    IntentCategory
)
from src.preprocessor import TweetPreprocessor
from src.intent_classifier import IntentClassifier
from src.knowledge_retriever import KnowledgeRetriever
from src.response_generator import ResponseGenerator
from src.automation_gatekeeper import AutomationGatekeeper
from src.decision_logger import decision_logger
from src.config import settings

logger = logging.getLogger(__name__)


class SupportAgentPipeline:
    def __init__(
        self,
        preprocessor: Optional[TweetPreprocessor] = None,
        classifier: Optional[IntentClassifier] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        generator: Optional[ResponseGenerator] = None,
        gatekeeper: Optional[AutomationGatekeeper] = None
    ):
        self.preprocessor = preprocessor or TweetPreprocessor()
        self.classifier = classifier or IntentClassifier()
        self.retriever = retriever or KnowledgeRetriever()
        self.classifier.set_retriever(self.retriever)
        self.generator = generator or ResponseGenerator()
        self.gatekeeper = gatekeeper or AutomationGatekeeper()
        logger.info("Initialized SupportAgentPipeline successfully.")

    def process_tweet(self, request: SupportAgentRequest) -> SupportAgentResponse:
        """
        Executes the full 5-stage customer support pipeline on an inbound tweet.
        """
        start_time = time.perf_counter()

        # 1. Preprocessing & Sanitization
        preprocessed = self.preprocessor.clean(request.tweet_text)

        # 2. Intent Classification & Sentiment Analysis
        intent_result = self.classifier.classify(preprocessed.cleaned_text)

        # 3. Grounded Exemplar Retrieval (RAG over historical brand pairs)
        exemplars = self.retriever.retrieve(
            query=preprocessed.cleaned_text,
            intent_filter=intent_result.primary_intent,
            top_k=settings.top_k_exemplars
        )

        # 4. Grounded Response Generation
        brand_context = request.brand_context or "Support"
        grounded_response = self.generator.generate_response(
            customer_query=preprocessed.cleaned_text,
            intent_result=intent_result,
            exemplars=exemplars,
            brand_name=brand_context
        )

        # 5. Automation Decision & Escalation Gate
        automation_decision = self.gatekeeper.evaluate(
            preprocessed=preprocessed,
            intent_result=intent_result,
            grounded_response=grounded_response
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response = SupportAgentResponse(
            inbound_tweet=request.tweet_text,
            preprocessed=preprocessed,
            intent_classification=intent_result,
            grounded_response=grounded_response,
            automation_decision=automation_decision,
            execution_time_ms=elapsed_ms
        )

        decision_logger.log(response)
        return response

    def process_batch(self, requests: List[SupportAgentRequest]) -> List[SupportAgentResponse]:
        """Processes multiple tweets sequentially or in batches."""
        return [self.process_tweet(req) for req in requests]

    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the pipeline capabilities and knowledge base."""
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "intents": [
                {
                    "name": intent.value,
                    "description": IntentClassifier.INTENT_DESCRIPTIONS.get(intent, "")
                }
                for intent in IntentCategory
            ],
            "total_indexed_exemplars": self.retriever.collection.count(),
            "confidence_threshold": settings.confidence_threshold,
            "max_tweet_characters": settings.max_tweet_characters
        }
