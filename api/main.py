"""
FastAPI REST API server for the AI Customer Support Agent.
Exposes endpoints for single tweet processing, batch triage, intent taxonomy,
health status, and serves the interactive dashboard UI.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.models import (
    SupportAgentRequest,
    SupportAgentResponse,
    IntentCategory
)
from src.pipeline import SupportAgentPipeline
from src.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade AI Support Agent for Twitter: Intent Classification, Grounded Response Generation, and Automation Triage."
)

# Enable CORS for local testing and external web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize single pipeline instance
pipeline = SupportAgentPipeline()

# Static Files & UI
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["Dashboard"])
async def root():
    """Serves the interactive web dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.app_name} API. Visit /docs for OpenAPI documentation."}


@app.post("/api/process", response_model=SupportAgentResponse, tags=["Agent Pipeline"])
async def process_tweet(request: SupportAgentRequest) -> SupportAgentResponse:
    """
    Process a single customer inbound tweet through the 5-stage AI pipeline:
    1. Preprocessing & PII Masking
    2. Intent Classification & Sentiment/Urgency Analysis
    3. Grounded Exemplar Retrieval (RAG via ChromaDB)
    4. Grounded Response Generation (Twitter-length bounded)
    5. Automation Decision & Escalation Triage with Audit Reasoning
    """
    try:
        return pipeline.process_tweet(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution error: {str(e)}"
        )


@app.post("/api/batch", response_model=List[SupportAgentResponse], tags=["Agent Pipeline"])
async def process_batch(requests: List[SupportAgentRequest]) -> List[SupportAgentResponse]:
    """Process a batch of customer tweets and return structured responses for each."""
    try:
        return pipeline.process_batch(requests)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch execution error: {str(e)}"
        )


@app.get("/api/intents", tags=["Metadata"])
async def get_intents() -> Dict[str, Any]:
    """Returns the defined intent taxonomy and descriptions."""
    return pipeline.get_metadata()


@app.get("/api/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Returns system status, model configurations, and indexed exemplar count."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "indexed_exemplars": pipeline.retriever.collection.count(),
        "gemini_active": bool(settings.gemini_api_key and not settings.force_local_fallback),
        "confidence_threshold": settings.confidence_threshold
    }


@app.get("/api/dataset", tags=["Dataset"])
async def get_dataset_samples(limit: int = 15) -> List[Dict[str, Any]]:
    """Returns sample historical customer support conversations from the knowledge base."""
    if not settings.dataset_path.exists():
        return []
    import json
    with open(settings.dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data[:limit]


@app.get("/api/logs", tags=["Audit Logs"])
async def get_decision_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns persistent decision audit trail records for compliance and review."""
    from src.decision_logger import decision_logger
    return decision_logger.get_recent_logs(limit=limit)

