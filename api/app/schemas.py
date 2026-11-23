"""Shared schemas and types."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Request to /v1/chat (main chat endpoint)."""
    message: str = Field(..., description="User's message")
    conversation_id: str = Field(..., description="Conversation/session ID")
    index_name: Optional[str] = Field(None, description="Knowledge index to search (required for RAG)")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    synthesis_prompt: Optional[str] = Field(None, description="Prompt for final synthesis")
    retry_reinforce: Optional[str] = Field(None, description="Text to reinforce on retry")
    guardrail_id: Optional[str] = Field(None, description="Guardrail ID to apply")
    guardrail_version: Optional[str] = Field(None, description="Guardrail version")
    page_id: Optional[str] = Field(None, description="Page ID for SingleStore KB backend")
    kb_backend: Optional[Literal["opensearch", "singlestore"]] = Field("opensearch", description="KB backend type")
    history: Optional[List[Message]] = Field(default_factory=list, description="Conversation history")
    stream: bool = Field(True, description="Stream response via SSE")


class WidgetChatRequest(BaseModel):
    """Request to /v1/widget/chat (embeddable widget)."""
    message: str = Field(..., description="User's message")
    conversation_id: str = Field(..., description="Conversation/session ID")
    index_name: Optional[str] = Field(None, description="Knowledge index to search")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    guardrail_id: Optional[str] = Field(None, description="Guardrail ID")
    guardrail_version: Optional[str] = Field(None, description="Guardrail version")
    history: Optional[List[Message]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    message: str
    conversation_id: str
    usage: Optional[dict] = None
    guardrail_action: Optional[str] = None
    kb_results_count: int = 0


class KBChunkRequest(BaseModel):
    """Request to add a chunk to the knowledge base."""
    text: str = Field(..., description="Text content of the chunk")
    doc_type: Optional[str] = Field("document", description="Document type")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")


class KBChunkResponse(BaseModel):
    status: str
    chunk_id: Optional[str] = None
    chunks_indexed: int = 0


class GuardrailRequest(BaseModel):
    """Request to create/update a guardrail."""
    name: str = Field(..., description="Guardrail name")
    description: Optional[str] = Field("", description="Description")
    rules: List[str] = Field(default_factory=list, description="List of rules/blocks")


class GuardrailResponse(BaseModel):
    status: str
    guardrail_id: str
    version: int = 1
    rules_count: int = 0


class DiscoverRequest(BaseModel):
    """Request to discover documents on a website."""
    url: str = Field(..., description="Base URL to discover")
    max_pages: int = Field(50, description="Maximum pages to discover")


class DiscoverResponse(BaseModel):
    status: str
    urls_found: int = 0
    urls: List[str] = Field(default_factory=list)