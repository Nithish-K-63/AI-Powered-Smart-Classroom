"""Document parsing, text extraction, and chunking pipeline for manuals."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import pypdf


class ManualDocumentProcessor:
    """Extracts text and metadata from PDF and TXT/Markdown manuals and splits into chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(
        self,
        file_path: Path | str,
        doc_id: str,
        title: str,
        equipment_category: str = "general_av",
    ) -> List[Dict[str, Any]]:
        """Parse file and return list of chunk dictionaries with metadata."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._process_pdf(path, doc_id, title, equipment_category)
        elif suffix in [".txt", ".md", ".log"]:
            return self._process_text(path, doc_id, title, equipment_category)
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Supported: .pdf, .txt, .md")

    def _process_pdf(
        self,
        path: Path,
        doc_id: str,
        title: str,
        equipment_category: str,
    ) -> List[Dict[str, Any]]:
        """Extract text page-by-page from PDF."""
        chunks: List[Dict[str, Any]] = []
        try:
            reader = pypdf.PdfReader(str(path))
            for page_idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                page_text = self._clean_text(page_text)
                if not page_text:
                    continue

                page_chunks = self._chunk_text(page_text)
                for chunk_idx, chunk_content in enumerate(page_chunks):
                    chunks.append({
                        "id": f"{doc_id}-p{page_idx}-c{chunk_idx}",
                        "doc_id": doc_id,
                        "title": title,
                        "filename": path.name,
                        "equipment_category": equipment_category,
                        "page_number": page_idx,
                        "chunk_index": chunk_idx,
                        "content": chunk_content,
                    })
        except Exception as e:
            raise RuntimeError(f"Error reading PDF '{path.name}': {e}")

        return chunks

    def _process_text(
        self,
        path: Path,
        doc_id: str,
        title: str,
        equipment_category: str,
    ) -> List[Dict[str, Any]]:
        """Process plain text / markdown file."""
        chunks: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()
            full_text = self._clean_text(full_text)
            text_chunks = self._chunk_text(full_text)

            for chunk_idx, chunk_content in enumerate(text_chunks):
                chunks.append({
                    "id": f"{doc_id}-c{chunk_idx}",
                    "doc_id": doc_id,
                    "title": title,
                    "filename": path.name,
                    "equipment_category": equipment_category,
                    "page_number": 1,
                    "chunk_index": chunk_idx,
                    "content": chunk_content,
                })
        except Exception as e:
            raise RuntimeError(f"Error reading text file '{path.name}': {e}")

        return chunks

    def _clean_text(self, text: str) -> str:
        """Normalize whitespaces and remove non-printable characters."""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks respecting sentence or word boundaries."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:].strip())
                break

            # Try to split at a sentence end or space
            split_idx = text.rfind(". ", start, end)
            if split_idx == -1 or split_idx < start + self.chunk_overlap:
                split_idx = text.rfind(" ", start, end)

            if split_idx == -1 or split_idx <= start:
                split_idx = end

            chunk = text[start:split_idx].strip()
            if chunk:
                chunks.append(chunk)

            start = max(split_idx + 1, start + self.chunk_size - self.chunk_overlap)

        return chunks

