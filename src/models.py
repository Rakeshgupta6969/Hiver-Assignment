"""
Data models and schemas for the AI Customer Support Agent.
Enforces strict contracts across the intent classification, retrieval,
generation, and automation decision stages.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """
    Mutually exclusive, collectively exhaustive (MECE) customer support intents
    tailored for Twitter customer interactions.
    """
    ORDER_DELIVERY_ISSUE = "ORDER_DELIVERY_ISSUE"
    BILLING_REFUND_INQUIRY = "BILLING_REFUND_INQUIRY"
    TECHNICAL_PRODUCT_SUPPORT = "TECHNICAL_PRODUCT_SUPPORT"
    ACCOUNT_SECURITY_ACCESS = "ACCOUNT_SECURITY_ACCESS"
    POLICY_GENERAL_FAQ = "POLICY_GENERAL_FAQ"
    COMPLAINT_FEEDBACK_ESCALATION = "COMPLAINT_FEEDBACK_ESCALATION"


class SentimentLevel(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    SEVERELY_DISSATISFIED = "SEVERELY_DISSATISFIED"


class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AutomationDecision(str, Enum):
    AUTOMATE = "AUTOMATE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class HistoricalExemplar(BaseModel):
    """A historical customer-brand interaction used as grounding context."""
    id: str
    brand: str
    customer_query: str
    brand_response: str
    intent: IntentCategory
    similarity_score: Optional[float] = Field(default=None, description="Cosine or retrieval similarity score")


class PreprocessedTweet(BaseModel):
    raw_text: str
    cleaned_text: str
    handles_detected: List[str] = Field(default_factory=list)
    contains_masked_pii: bool = False
    original_length: int
    cleaned_length: int


class IntentClassificationResult(BaseModel):
    primary_intent: IntentCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    secondary_intent: Optional[IntentCategory] = None
    sentiment: SentimentLevel
    urgency: UrgencyLevel
    reasoning: str = Field(description="Explanation of why this intent was selected")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)


class GroundedResponseResult(BaseModel):
    generated_reply: str = Field(description="Customer reply adhering to Twitter constraints")
    grounded_in_exemplars: List[HistoricalExemplar] = Field(default_factory=list)
    character_count: int
    direct_message_suggested: bool = Field(description="Whether the response invites customer to DM for secure resolution")
    tone: str = Field(description="Tone classification of the generated response")


class AutomationGateResult(BaseModel):
    decision: AutomationDecision
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Detailed rationale for the automation or escalation decision")
    urgency: UrgencyLevel
    routing_team: str = Field(description="Assigned human team if escalated, or automated queue if automated")
    risk_factors: List[str] = Field(default_factory=list)


class SupportAgentRequest(BaseModel):
    tweet_text: str = Field(..., min_length=2, max_length=1000, description="Customer inbound tweet")
    author_id: Optional[str] = Field(default="customer_user", description="Optional Twitter author ID")
    brand_context: Optional[str] = Field(default="Support", description="Brand name, e.g. AmazonHelp, AppleSupport, Hiver")


class SupportAgentResponse(BaseModel):
    inbound_tweet: str
    preprocessed: PreprocessedTweet
    intent_classification: IntentClassificationResult
    grounded_response: GroundedResponseResult
    automation_decision: AutomationGateResult
    execution_time_ms: float
