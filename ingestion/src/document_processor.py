"""Document processor for ingestion pipeline."""
import os
import re
from typing import Dict, List, Optional, Tuple

from ingestion.src.chroma_store import ChromaKB


class DocumentProcessor:
    """Processes documents for the ingestion pipeline."""

    def __init__(self, kb_store: Optional[ChromaKB] = None):
        self.kb_store = kb_store or ChromaKB()

    def process_text(
        self,
        text: str,
        doc_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> int:
        """Process a text document into chunks and index them."""
        chunks = self._chunk_text(text, chunk_size, overlap)
        count = 0
        for chunk in chunks:
            self.kb_store.add_chunk(
                text=chunk,
                doc_type=doc_type,
                metadata=metadata,
            )
            count += 1
        return count

    def process_file(
        self,
        file_path: str,
        doc_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Process a file (txt, md, html)."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".txt", ".md"):
            text = self._read_text(file_path)
        elif ext == ".html":
            text = self._read_html(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if doc_type is None:
            doc_type = ext.lstrip(".")

        if metadata is None:
            metadata = {"source": file_path}

        return self.process_text(text, doc_type, metadata)

    def process_url(
        self,
        url: str,
        doc_type: str = "web",
        max_pages: int = 50,
    ) -> int:
        """Discover and process URLs (mock for local dev)."""
        # Mock: return a few example URLs
        base = url.rstrip("/")
        mock_urls = [
            f"{base}/page/1",
            f"{base}/page/2",
            f"{base}/about",
            f"{base}/contact",
        ]

        count = 0
        for discovered_url in mock_urls[:max_pages]:
            # Mock content
            content = f"Content from {discovered_url}"
            self.kb_store.add_chunk(
                text=content,
                doc_type=doc_type,
                metadata={"source": discovered_url},
            )
            count += 1
        return count

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:].strip())
                break

            # Find a natural break point
            break_point = text.rfind(".", start, end)
            if break_point > start + chunk_size // 2:
                end = break_point + 1
            else:
                break_point = text.rfind(" ", start, end)
                if break_point > start + chunk_size // 2:
                    end = break_point

            chunks.append(text[start:end].strip())
            start = end - overlap

        return [c for c in chunks if c]

    def _read_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_html(self, file_path: str) -> str:
        """Extract text from HTML (simple regex-based)."""
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text