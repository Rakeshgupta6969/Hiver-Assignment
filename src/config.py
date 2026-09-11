"""
Configuration settings for the AI Customer Support Agent.
"""

import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
DATASET_PATH = DATA_DIR / "twitter_support_conversations.json"


class Settings(BaseModel):
    app_name: str = "Hiver AI Customer Support Agent"
    app_version: str = "1.0.0"
    
    # LLM Settings
    gemini_api_key: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    openai_api_key: str = os.getenv("OPENAI_API_KEY") or ""
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    
    # Vector Database Settings
    chroma_persist_dir: Path = CHROMA_DIR
    dataset_path: Path = DATASET_PATH
    top_k_exemplars: int = 3
    
    # Thresholds for Automation
    confidence_threshold: float = 0.75
    similarity_threshold: float = 0.45
    max_tweet_characters: int = 280
    
    # Execution mode
    force_local_fallback: bool = os.getenv("FORCE_LOCAL_FALLBACK", "false").lower() == "true"


settings = Settings()
