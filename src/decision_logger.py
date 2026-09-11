"""
Decision Audit Logging module for the AI Customer Support Agent.
Maintains an append-only JSONL audit log of all triage decisions,
enabling regulatory compliance, triage inspection, and performance monitoring.
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.models import SupportAgentResponse
from src.config import settings

logger = logging.getLogger(__name__)


class DecisionLogger:
    def __init__(self, log_dir: Optional[Path] = None):
        base_dir = settings.chroma_persist_dir.parent.parent
        self.log_dir = log_dir or (base_dir / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "decision_audit.jsonl"
        self._lock = threading.Lock()

    def log(self, response: SupportAgentResponse, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Appends a structured audit record of the customer conversation triage.
        """
        record_id = request_id or str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        top_similarity = 0.0
        if response.grounded_response.grounded_in_exemplars:
            top_similarity = response.grounded_response.grounded_in_exemplars[0].similarity_score or 0.0

        audit_entry = {
            "record_id": record_id,
            "timestamp": timestamp,
            "inbound_tweet": response.inbound_tweet,
            "cleaned_tweet": response.preprocessed.cleaned_text,
            "contains_masked_pii": response.preprocessed.contains_masked_pii,
            "intent": response.intent_classification.primary_intent.value,
            "intent_confidence": response.intent_classification.confidence,
            "sentiment": response.intent_classification.sentiment.value,
            "urgency": response.intent_classification.urgency.value,
            "retrieved_exemplars_count": len(response.grounded_response.grounded_in_exemplars),
            "top_exemplar_similarity": top_similarity,
            "generated_reply": response.grounded_response.generated_reply,
            "dm_suggested": response.grounded_response.direct_message_suggested,
            "decision": response.automation_decision.decision.value,
            "decision_confidence": response.automation_decision.confidence,
            "routing_team": response.automation_decision.routing_team,
            "decision_reasoning": response.automation_decision.reasoning,
            "risk_factors": response.automation_decision.risk_factors,
            "execution_time_ms": response.execution_time_ms
        }

        try:
            with self._lock:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(audit_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write decision audit log: {e}")

        return audit_entry

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent audit logs in reverse chronological order."""
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with self._lock:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read decision audit logs: {e}")
            return []

        return entries[-limit:][::-1]


decision_logger = DecisionLogger()
