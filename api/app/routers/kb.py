"""KB ingestion routes: /v1/kb/chunks, /v1/kb/discover."""
import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import (
    KBChunkRequest, KBChunkResponse,
    DiscoverRequest, DiscoverResponse,
)
from app.config import API_KEY
from ingestion.src.chroma_store import ChromaKB


router = APIRouter(prefix="/v1/kb", tags=["knowledge-base"])

kb_store = ChromaKB()


def _require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing x-api-key")


@router.post("/chunks", response_model=KBChunkResponse)
async def add_chunks(
    request: KBChunkRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Add a text chunk to the knowledge base.
    """
    _require_api_key(x_api_key)

    chunk_id = kb_store.add_chunk(
        text=request.text,
        doc_type=request.doc_type,
        metadata=request.metadata,
    )
    count = kb_store.get_count()

    return KBChunkResponse(
        status="indexed",
        chunk_id=chunk_id,
        chunks_indexed=count,
    )


@router.post("/chunks/batch")
async def add_chunks_batch(
    chunks: list[KBChunkRequest],
    x_api_key: Optional[str] = Header(None),
):
    """
    Add multiple chunks in a batch.
    """
    _require_api_key(x_api_key)

    added = 0
    for chunk_req in chunks:
        kb_store.add_chunk(
            text=chunk_req.text,
            doc_type=chunk_req.doc_type,
            metadata=chunk_req.metadata,
        )
        added += 1

    return {
        "status": "indexed",
        "chunks_added": added,
        "total_chunks": kb_store.get_count(),
    }


@router.get("/chunks")
async def list_chunks(
    limit: int = 20,
    x_api_key: Optional[str] = Header(None),
):
    """
    List chunks in the knowledge base.
    """
    _require_api_key(x_api_key)
    chunks = kb_store.search("", n_results=limit)
    return {"chunks": chunks, "total": kb_store.get_count()}


@router.delete("/chunks")
async def clear_chunks(
    x_api_key: Optional[str] = Header(None),
):
    """
    Clear all chunks from the knowledge base.
    """
    _require_api_key(x_api_key)
    kb_store.clear()
    return {"status": "cleared"}


@router.post("/discover", response_model=DiscoverResponse)
async def discover_urls(
    request: DiscoverRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Discover URLs on a website (simplified mock).
    In production this would crawl a website and return discovered URLs
    for indexing. Here it returns a mock response.
    """
    _require_api_key(x_api_key)

    # Mock discovery: return a few example URLs
    base = request.url.rstrip("/")
    mock_urls = [
        f"{base}/page/1",
        f"{base}/page/2",
        f"{base}/about",
        f"{base}/contact",
    ]

    return DiscoverResponse(
        status="discovered",
        urls_found=min(len(mock_urls), request.max_pages),
        urls=mock_urls[:request.max_pages],
    )