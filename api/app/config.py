"""Configuration for local dev replica."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.environ.get("APP_ENV", "local")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")

# Default index when none provided (for testing only)
DEFAULT_INDEX = os.environ.get("DEFAULT_INDEX", "local-kb")

# Chroma settings
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", str(Path(__file__).resolve().parents[3] / "ingestion" / "chroma_db"))

# API key for auth (x-api-key header)
API_KEY = os.environ.get("API_KEY", "local-dev-key")

# Mock agent settings
MOCK_AGENT_ENABLED = os.environ.get("MOCK_AGENT_ENABLED", "True").lower() == "true"
MOCK_RESPONSE_DELAY_MS = int(os.environ.get("MOCK_RESPONSE_DELAY_MS", "0"))

# Guardrail settings
GUARDRAIL_ENABLED = os.environ.get("GUARDRAIL_ENABLED", "True").lower() == "true"
GUARDRAIL_DEFAULT_ID = os.environ.get("GUARDRAIL_DEFAULT_ID", "local-guardrail-v1")
GUARDRAIL_DEFAULT_VERSION = os.environ.get("GUARDRAIL_DEFAULT_VERSION", "1")

# SSE settings
SSE_PING_INTERVAL_SEC = int(os.environ.get("SSE_PING_INTERVAL_SEC", "30"))