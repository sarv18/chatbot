"""Chroma vector store for local knowledge base."""
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

from app.config import CHROMA_PERSIST_DIR


class ChromaKB:
    """Local ChromaDB knowledge base for document chunks."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        # Default collection for local development
        self.collection = self.client.get_or_create_collection(
            name="local-kb",
            metadata={"description": "Local KB for chatbot development"},
        )

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

        col.add(
            documents=[text],
            metadatas=[meta],
            ids=[chunk_id],
        )
        return chunk_id

    def search(
        self,
        query: str,
        n_results: int = 5,
        collection_name: Optional[str] = None,
    ) -> List[Tuple[str, Dict[str, Any], Optional[float]]]:
        """Search the knowledge base. Returns (document, metadata, distance)."""
        col = self._get_collection(collection_name)
        if col.count() == 0:
            return []

        results = col.query(
            query_texts=[query],
            n_results=n_results,
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        return list(zip(docs, metas, dists))

    def get_collection(self, name: str):
        """Get or create a collection by name."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"description": f"KB collection: {name}"},
        )

    def _get_collection(self, name: Optional[str] = None):
        if name and name != "local-kb":
            return self.get_collection(name)
        return self.collection

    def get_count(self, collection_name: Optional[str] = None) -> int:
        """Get total chunk count."""
        col = self._get_collection(collection_name)
        return col.count()

    def clear(self, collection_name: Optional[str] = None) -> int:
        """Clear all chunks from a collection."""
        col = self._get_collection(collection_name)
        if col.count() > 0:
            # Chroma doesn't have a direct clear, so delete all IDs
            all_ids = col.get()["ids"]
            if all_ids:
                col.delete(ids=all_ids)
        return 0

    def list_collections(self) -> List[str]:
        """List all collection names."""
        return [c.name for c in self.client.list_collections()]


# Convenience singleton
_chroma_kb = None


def get_chroma_kb() -> ChromaKB:
    global _chroma_kb
    if _chroma_kb is None:
        _chroma_kb = ChromaKB()
    return _chroma_kb