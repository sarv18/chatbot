"""Simple in-memory KB store for local development (no chromadb dependency)."""
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple


class ChromaKB:
    """Local in-memory knowledge base for document chunks."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir
        self._collections: Dict[str, Dict[str, Dict]] = {}
        self._default_collection = "local-kb"
        self._ensure_collection(self._default_collection)

    def _ensure_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = {}

    def add_chunk(
        self,
        text: str,
        doc_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> str:
        """Add a text chunk to the knowledge base."""
        col = self._get_collection(collection_name)

        chunk_id = str(uuid.uuid4())[:8]
        meta = {
            "doc_type": doc_type,
            "chunk_id": chunk_id,
        }
        if metadata:
            meta.update(metadata)

        col[chunk_id] = {
            "text": text,
            "metadata": meta,
        }
        return chunk_id

    def search(
        self,
        query: str,
        n_results: int = 5,
        collection_name: Optional[str] = None,
    ) -> List[Tuple[str, Dict[str, Any], Optional[float]]]:
        """Search the knowledge base (simple keyword matching)."""
        col = self._get_collection(collection_name)
        if not col:
            return []

        query_lower = query.lower()
        results = []

        for chunk_id, data in col.items():
            text = data["text"]
            meta = data["metadata"]
            # Simple relevance: count query words in text
            relevance = sum(1 for word in query_lower.split() if word in text.lower())
            if relevance > 0:
                distance = 1.0 - (relevance / max(len(query_lower.split()), 1))
                results.append((text, meta, distance))

        # Sort by relevance (lower distance = more relevant)
        results.sort(key=lambda x: x[2] if x[2] is not None else 1.0)
        return results[:n_results]

    def get_collection(self, name: str):
        """Get or create a collection by name."""
        self._ensure_collection(name)
        return self._collections[name]

    def _get_collection(self, name: Optional[str] = None):
        if name and name != self._default_collection:
            self._ensure_collection(name)
            return self._collections[name]
        return self._collections[self._default_collection]

    def get_count(self, collection_name: Optional[str] = None) -> int:
        """Get total chunk count."""
        col = self._get_collection(collection_name)
        return len(col)

    def clear(self, collection_name: Optional[str] = None) -> int:
        """Clear all chunks from a collection."""
        col = self._get_collection(collection_name)
        count = len(col)
        col.clear()
        return count

    def list_collections(self) -> List[str]:
        """List all collection names."""
        return list(self._collections.keys())


# Convenience singleton
_chroma_kb = None


def get_chroma_kb() -> ChromaKB:
    global _chroma_kb
    if _chroma_kb is None:
        _chroma_kb = ChromaKB()
    return _chroma_kb