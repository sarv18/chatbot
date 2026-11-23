"""FastAPI app entrypoint for chatbot local dev replica."""
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Prepend repo root to path so agent/ingestion imports resolve
# REPO_ROOT is three levels up from api/app/: api/app/main.py -> api -> chatbot
_REPO_ROOT = Path(__file__).parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.routers import chat, kb, guardrail
from app.config import DEBUG


app = FastAPI(
    title="Chatbot API (Local Dev Replica)",
    description="Local development replica of Locobuzz chatbot API with SSE streaming",
    version="0.1.0",
    debug=DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(kb.router)
app.include_router(guardrail.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chatbot-api-local"}


@app.get("/")
async def root():
    return {
        "service": "Chatbot API (Local Dev Replica)",
        "version": "0.1.0",
        "endpoints": {
            "chat": "/v1/chat",
            "widget_chat": "/v1/widget/chat",
            "kb_chunks": "/v1/kb/chunks",
            "kb_discover": "/v1/kb/discover",
            "guardrail": "/v1/guardrail",
            "health": "/health",
        },
        "auth": "x-api-key header required",
    }