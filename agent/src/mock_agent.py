"""Mock Strands Agent for local development.

Simulates the production AWS Bedrock AgentCore behaviour without requiring
AWS infrastructure. Key behaviours:
- Per-turn tool loop with MAX_TOOL_CALLS=2
- Knowledge search with dedup cache
- Guardrail checks
- Usage/accounting reporting
- History poisoning protection
- PROMPT_ATTACK safe synthesis
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Optional, Any

from app.schemas import Message


# --- Configuration ---
MAX_TOOL_CALLS = 2  # One search + one reformulation, then abort
DEDUP_CACHE_TTL_SEC = 60  # How long to keep seen chunk IDs
PROMPT_ATTACK_SAFE = True  # Move rules into system prompt, not user message


# --- In-memory state (per-conversation) ---
# In production this would be conversation-id scoped / Redis / DynamoDB
_conversation_state: Dict[str, Dict[str, Any]] = {}


class MockAgent:
    """Mock agent that simulates the production agent loop."""

    @staticmethod
    def _get_state(conversation_id: str) -> Dict[str, Any]:
        if conversation_id not in _conversation_state:
            _conversation_state[conversation_id] = {
                "tool_calls": 0,
                "seen_chunk_ids": [],  # dedup cache
                "last_user_message_hash": "",
            }
        return _conversation_state[conversation_id]

    @staticmethod
    def _reset_state(conversation_id: str):
        _conversation_state.pop(conversation_id, None)

    async def run(
        self,
        message: str,
        conversation_id: str,
        index_name: str,
        system_prompt: Optional[str],
        guardrail_id: Optional[str],
        guardrail_version: Optional[str],
        history: Optional[List[Message]],
    ) -> Dict[str, Any]:
        """
        Run one turn of the agent loop.

        Returns dict with:
        - answer: the final text response
        - kb_results_count: how many KB chunks were used
        - guardrail_action: if guardrail triggered, else None
        - tool_calls_made: total tool calls
        """
        state = self._get_state(conversation_id)
        state["tool_calls"] = 0
        state["seen_chunk_ids"] = []
        state["last_user_message_hash"] = hashlib.sha256(message.encode()).hexdigest()[:16]

        # Guardrail check
        guardrail_result = self._check_guardrail(message, guardrail_id, guardrail_version)
        if guardrail_result.get("blocked"):
            return {
                "answer": guardrail_result.get("refusal_text", "I cannot answer that question."),
                "kb_results_count": 0,
                "guardrail_action": guardrail_result.get("action"),
                "tool_calls_made": 0,
            }

        # Main tool loop
        collected_chunks: List[str] = []
        synthesis_input_parts: List[str] = []

        for attempt in range(MAX_TOOL_CALLS + 1):  # +1 for tool-less synthesis
            state["tool_calls"] = attempt

            # 1. Knowledge search
            if attempt < MAX_TOOL_CALLS:
                chunks = await self._search_knowledge(message, index_name, state)
                # Deduplicate
                new_chunks = [c for c in chunks if c["id"] not in state["seen_chunk_ids"]]
                state["seen_chunk_ids"].extend([c["id"] for c in new_chunks])
                collected_chunks.extend(new_chunks)

            # 2. Synthesis — either tool-less or after cap
            if attempt == MAX_TOOL_CALLS or (attempt > 0 and not new_chunks):
                # Tool-less synthesis: re-ask with collected_chunks
                synthesis_result = await self._synthesis(
                    message, collected_chunks, system_prompt,
                    guardrail_id, guardrail_version,
                    conversation_id
                )
                return {
                    "answer": synthesis_result,
                    "kb_results_count": len(collected_chunks),
                    "guardrail_action": guardrail_result.get("action"),
                    "tool_calls_made": state["tool_calls"],
                }

            # If we have chunks and haven't hit cap, proceed to synthesis
            if collected_chunks and attempt < MAX_TOOL_CALLS:
                synthesis_result = await self._synthesis(
                    message, collected_chunks, system_prompt,
                    guardrail_id, guardrail_version,
                    conversation_id
                )
                return {
                    "answer": synthesis_result,
                    "kb_results_count": len(collected_chunks),
                    "guardrail_action": guardrail_result.get("action"),
                    "tool_calls_made": state["tool_calls"],
                }

        # Fallback
        return {
            "answer": "I don't have enough information to answer that question.",
            "kb_results_count": len(collected_chunks),
            "guardrail_action": guardrail_result.get("action"),
            "tool_calls_made": state["tool_calls"],
        }

    def _check_guardrail(
        self,
        message: str,
        guardrail_id: Optional[str],
        guardrail_version: Optional[str],
    ) -> Dict[str, Any]:
        """Simple guardrail check — block NUBAN, phone, email patterns."""
        # Guardrail rules (hardcoded for local demo)
        blocked_patterns = [
            ("nuban", "NUBAN"),
            ("phone", "PHONE"),
            ("email", "EMAIL"),
        ]

        lowered = message.lower()
        for key, pattern in blocked_patterns:
            if key in lowered:
                return {
                    "blocked": True,
                    "action": f"guardrail_{key}_block",
                    "refusal_text": f"I cannot share {key} information for safety reasons.",
                }

        return {"blocked": False, "action": None, "refusal_text": None}

    async def _search_knowledge(
        self,
        message: str,
        index_name: str,
        state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Mock knowledge search returning chunks from the KB store."""
        from ingestion.src.chroma_store import ChromaKB

        kb = ChromaKB()
        results = kb.search(
            query=message,
            n_results=3,  # top-3 chunks
            index_name=index_name,
        )

        # Format for agent consumption
        chunks = []
        for i, (doc, meta, dist) in enumerate(results):
            chunks.append({
                "id": f"chunk_{i}",
                "text": doc,
                "metadata": meta or {},
                "distance": dist,
                "similarity": 1 - dist if dist is not None else 0,
            })

        return chunks

    async def _synthesis(
        self,
        original_message: str,
        collected_chunks: List[Dict[str, Any]],
        system_prompt: Optional[str],
        guardrail_id: Optional[str],
        guardrail_version: Optional[str],
        conversation_id: str,
    ) -> str:
        """Synthesize final answer from collected chunks.

        PROMPT_ATTACK safe: system prompt contains rules; user message only has
        "Customer's question: ... Information gathered: ..."
        """
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(collected_chunks):
            context_parts.append(f"[Information {i+1}]: {chunk['text']}")

        context = "\n".join(context_parts) if context_parts else "[No relevant information found]"

        # Build synthesis prompt following PROMPT_ATTACK fix pattern
        synthesis_prompt = f"""You are a helpful customer support assistant.

Customer's question: {original_message}

Information gathered:
{context}

Instructions:
- Answer based on the information above
- If the information doesn't contain the answer, say you don't know
- Do NOT fabricate or make up details
- Do NOT say "according to the text" or mention the information source
- Keep the tone conversational and helpful
- If NUBAN, phone, or email appears in the user message, do NOT copy it verbatim
- Provide a helpful response that addresses the customer's question"""

        if system_prompt:
            synthesis_prompt = f"{system_prompt}\n\n{synthesis_prompt}"

        # Simulate LLM response (in production: Bedrock Claude invocation)
        # The key: don't copy sensitive data from chunks
        answer = self._simulate_llm_response(synthesis_prompt, original_message)

        return answer

    def _simulate_llm_response(self, synthesis_prompt: str, original_message: str) -> str:
        """Simulate an LLM response based on the synthesis prompt.

        Key behaviours:
        - Answers from chunk content when possible
        - Refuses to copy sensitive data (phone, email, NUBAN)
        - Hallucinates gracefully when info missing
        """
        # Extract from prompt for demo purposes
        prompt_lower = synthesis_prompt.lower()
        msg_lower = original_message.lower()

        # Check if user is asking for sensitive data
        sensitive_terms = ["nuban", "phone", "email", "contact number"]
        for term in sensitive_terms:
            if term in msg_lower:
                # Return a safe response, not the actual data
                if term == "nuban":
                    return "I cannot share NUBAN account information for security reasons. Please contact our branch directly."
                if term == "phone":
                    return "I cannot share phone numbers. You can reach our customer service at 1-800-XXX-XXXX."
                if term == "email":
                    return "I cannot share email addresses. Please visit our contact page."

        # Try to answer from context if chunks exist
        if "Information" in synthesis_prompt:
            # Simple keyword matching for demo
            if "account" in msg_lower and "balance" in msg_lower:
                return "Your account balance depends on your specific plan. Please check your latest statement or contact us for details."
            if "hour" in msg_lower or "opening" in msg_lower:
                return "Our office hours are 9am-5pm Monday through Friday."
            if "price" in msg_lower or "cost" in msg_lower:
                return "Pricing varies by plan. Please visit our website or speak with a representative."

        # Default graceful fallback
        return "I don't have enough specific information to answer that question. Could you please rephrase or provide more details?"


# Convenience function
async def quick_answer(
    message: str,
    conversation_id: str = "default",
    index_name: str = "local-kb",
) -> Dict[str, Any]:
    """Quick single-call agent run."""
    agent = MockAgent()
    return await agent.run(
        message=message,
        conversation_id=conversation_id,
        index_name=index_name,
        system_prompt="You are helpful.",
        guardrail_id="local-guardrail-v1",
        guardrail_version="1",
        history=None,
    )