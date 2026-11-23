"""Guardrail store for local development."""
import time
from typing import Any, Dict, List, Optional


class GuardrailStore:
    """In-memory guardrail store with version tracking."""

    def __init__(self):
        self.guardrails: Dict[str, Dict[str, Any]] = {}
        self.next_version: int = 1

    def create_or_update(self, name: str, description: str, rules: List[str]) -> Dict[str, Any]:
        """Create or update a guardrail by name."""
        existing = self.guardrails.get(name)
        if existing and existing.get("version"):
            # Increment version
            version = existing["version"] + 1
        else:
            version = self.next_version
            self.next_version += 1

        record = {
            "guardrail_id": f"{name}_v{version}",
            "name": name,
            "version": version,
            "description": description,
            "rules": rules,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        self.guardrails[name] = record
        return record

    def get(self, guardrail_id: str) -> Optional[Dict[str, Any]]:
        """Get a guardrail by ID like 'name_v{n}'."""
        for g in self.guardrails.values():
            if g.get("guardrail_id") == guardrail_id:
                return g
        return None

    def list_all(self) -> List[Dict[str, Any]]:
        """List all guardrails."""
        return list(self.guardrails.values())


# Convenience singleton
_guardrail_store = GuardrailStore()


def get_guardrail_store() -> GuardrailStore:
    return _guardrail_store


def reset_guardrail_store() -> None:
    """Reset the store (for tests)."""
    _guardrail_store.guardrails.clear()
    _guardrail_store.next_version = 1


def create_or_update_guardrail(name: str, description: str, rules: List[str]) -> Dict[str, Any]:
    return _guardrail_store.create_or_update(name, description, rules)


def get_guardrail(guardrail_id: str) -> Optional[Dict[str, Any]]:
    return _guardrail_store.get(guardrail_id)


def list_guardrails() -> List[Dict[str, Any]]:
    return _guardrail_store.list_all()