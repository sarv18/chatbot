"""Guardrail routes: /v1/guardrail (create/read)."""
from typing import Optional
from fastapi import APIRouter, Header, HTTPException

from app.schemas import GuardrailRequest, GuardrailResponse
from app.config import API_KEY, GUARDRAIL_DEFAULT_ID, GUARDRAIL_DEFAULT_VERSION
from agent.src.guardrail import GuardrailStore


router = APIRouter(prefix="/v1/guardrail", tags=["guardrails"])

guardrail_store = GuardrailStore()


def _require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing x-api-key")


@router.post("", response_model=GuardrailResponse)
async def create_guardrail(
    request: GuardrailRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Create or update a guardrail with a list of rules.
    """
    _require_api_key(x_api_key)

    record = guardrail_store.create_or_update(
        name=request.name,
        description=request.description,
        rules=request.rules,
    )

    return GuardrailResponse(
        status="created",
        guardrail_id=record["guardrail_id"],
        version=record["version"],
        rules_count=len(record["rules"]),
    )


@router.get("/{guardrail_id}")
async def get_guardrail(
    guardrail_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """
    Read a guardrail by ID.
    """
    _require_api_key(x_api_key)
    record = guardrail_store.get(guardrail_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Guardrail {guardrail_id} not found")
    return record


@router.get("")
async def list_guardrails(
    x_api_key: Optional[str] = Header(None),
):
    """
    List all guardrails.
    """
    _require_api_key(x_api_key)
    return {"guardrails": guardrail_store.list_all()}