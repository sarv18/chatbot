"""Chat routes: /v1/chat and /v1/widget/chat with SSE streaming."""
import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas import (
    ChatRequest, WidgetChatRequest, ChatResponse,
    Message,
)
from app.config import (
    API_KEY, DEFAULT_INDEX, GUARDRAIL_DEFAULT_ID,
    GUARDRAIL_DEFAULT_VERSION, GUARDRAIL_ENABLED,
    MOCK_AGENT_ENABLED, MOCK_RESPONSE_DELAY_MS,
)
from agent.src.mock_agent import MockAgent
from ingestion.src.chroma_store import ChromaKB


router = APIRouter(prefix="/v1", tags=["chat"])

# Singleton instances (mock agent + KB store)
mock_agent = MockAgent()
kb_store = ChromaKB()


def _require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing x-api-key")


async def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/chat", response_model=None)
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
    stream: Optional[bool] = Query(None, description="Override streaming"),
):
    """
    Main chat endpoint. Accepts per-request config (index_name, system_prompt,
    guardrail_id, guardrail_version). Refuses if required config missing.
    Streams SSE frames: intro/token/usage/error/done.
    """
    _require_api_key(x_api_key)

    # Validate required config — no fallbacks (per blueprint §1.2)
    index_name = request.index_name or DEFAULT_INDEX
    system_prompt = request.system_prompt or "You are a helpful assistant."
    guardrail_id = request.guardrail_id or GUARDRAIL_DEFAULT_ID
    guardrail_version = request.guardrail_version or GUARDRAIL_DEFAULT_VERSION

    effective_stream = stream if stream is not None else request.stream

    async def event_generator():
        try:
            start_time = time.time()

            # Intro frame
            yield await _sse_event({
                "event": "intro",
                "conversation_id": request.conversation_id,
                "index_name": index_name,
            })

            # Simulate processing delay
            if MOCK_RESPONSE_DELAY_MS > 0:
                await asyncio.sleep(MOCK_RESPONSE_DELAY_MS / 1000.0)

            # Run mock agent
            result = await mock_agent.run(
                message=request.message,
                conversation_id=request.conversation_id,
                index_name=index_name,
                system_prompt=system_prompt,
                guardrail_id=guardrail_id,
                guardrail_version=guardrail_version,
                history=request.history,
            )

            usage_ms = int((time.time() - start_time) * 1000)

            # Guardrail frame if applicable
            if result.get("guardrail_action"):
                yield await _sse_event({
                    "event": "guardrail",
                    "action": result["guardrail_action"],
                    "guardrail_id": guardrail_id,
                })

            # Stream tokens (mock)
            full_text = result.get("answer", "")
            words = full_text.split()
            for i, word in enumerate(words):
                yield await _sse_event({
                    "event": "token",
                    "token": word + (" " if i < len(words) - 1 else ""),
                })
                await asyncio.sleep(0.01)  # simulate streaming

            # Usage frame
            elapsed_ms = int((time.time() - start_time) * 1000)
            yield await _sse_event({
                "event": "usage",
                "tokens_in": len(request.message.split()),
                "tokens_out": len(words),
                "kb_results": result.get("kb_results_count", 0),
                "elapsed_ms": elapsed_ms,
            })

            # Done frame
            yield await _sse_event({
                "event": "done",
                "conversation_id": request.conversation_id,
                "message_id": f"msg_{int(time.time()*1000)}",
            })

        except Exception as e:
            yield await _sse_event({
                "event": "error",
                "error": str(e),
            })

    if effective_stream:
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Non-streaming: collect all and return once
        collected = ""
        kb_count = 0
        guardrail_action = None
        async for chunk in event_generator():
            if chunk.startswith("data: "):
                data = json.loads(chunk[6:])
                if data.get("event") == "token":
                    collected += data.get("token", "")
                elif data.get("event") == "usage":
                    kb_count = data.get("kb_results", 0)
                elif data.get("event") == "guardrail":
                    guardrail_action = data.get("action")
        return ChatResponse(
            message=collected,
            conversation_id=request.conversation_id,
            usage={"tokens_in": len(request.message.split()), "tokens_out": len(collected.split())},
            guardrail_action=guardrail_action,
            kb_results_count=kb_count,
        )


@router.post("/widget/chat")
async def widget_chat(
    request: WidgetChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Widget chat endpoint. Returns token frames; terminal frame is `final` with message_id.
    Simplified version of /chat for embeddable widgets.
    """
    _require_api_key(x_api_key)

    index_name = request.index_name or DEFAULT_INDEX
    system_prompt = request.system_prompt or "You are a helpful assistant."
    guardrail_id = request.guardrail_id or GUARDRAIL_DEFAULT_ID
    guardrail_version = request.guardrail_version or GUARDRAIL_DEFAULT_VERSION

    async def event_generator():
        try:
            start_time = time.time()
            yield await _sse_event({"event": "intro", "conversation_id": request.conversation_id})

            result = await mock_agent.run(
                message=request.message,
                conversation_id=request.conversation_id,
                index_name=index_name,
                system_prompt=system_prompt,
                guardrail_id=guardrail_id,
                guardrail_version=guardrail_version,
                history=request.history,
            )

            if result.get("guardrail_action"):
                yield await _sse_event({
                    "event": "guardrail",
                    "action": result["guardrail_action"],
                })

            full_text = result.get("answer", "")
            words = full_text.split()
            for i, word in enumerate(words):
                yield await _sse_event({
                    "event": "token",
                    "text": word + (" " if i < len(words) - 1 else ""),
                })
                await asyncio.sleep(0.01)

            elapsed_ms = int((time.time() - start_time) * 1000)
            yield await _sse_event({
                "event": "final",
                "message_id": f"widget_msg_{int(time.time()*1000)}",
                "conversation_id": request.conversation_id,
                "elapsed_ms": elapsed_ms,
            })
        except Exception as e:
            yield await _sse_event({"event": "error", "error": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")