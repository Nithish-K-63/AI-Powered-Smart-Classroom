"""Vector Store & Retrieval Pipeline for Smart Classroom AV Manuals.

Supports ChromaDB persistent vector database with an automatic resilient in-memory
vector/TF-IDF similarity fallback so the application is always rock-solid.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_PERSIST_DIR = ROOT_DIR / "data" / "chroma_db"


class AVVectorStore:
    """Hybrid ChromaDB / Semantic vector store for approved campus SOPs & manuals."""

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = "classroom_av_manuals"
        self.chroma_client = None
        self.collection = None
        self.backend_type = "chromadb"

        # In-memory document storage for fast metadata resolution and fallback
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None

        self._init_backend()
        self._load_existing_manuals()

    def _load_existing_manuals(self) -> None:
        """Scan campus_manuals directory on startup and auto-index any existing manuals."""
        if self.documents:
            return
        if self.collection is not None:
            try:
                if self.collection.count() > 0:
                    return
            except Exception:
                pass
        manuals_dir = ROOT_DIR / "data" / "campus_manuals"
        if not manuals_dir.exists():
            return
        try:
            from .document_processor import ManualDocumentProcessor
            processor = ManualDocumentProcessor(chunk_size=400, chunk_overlap=60)
            all_chunks = []
            for file_path in manuals_dir.glob("*.*"):
                if file_path.suffix.lower() in [".pdf", ".txt", ".md"]:
                    cat = "general_av"
                    name_lower = file_path.stem.lower()
                    for c in ["projector", "smart_board", "microphone", "speaker", "display"]:
                        if c in name_lower:
                            cat = c
                            break
                    chunks = processor.process_file(
                        file_path=file_path,
                        doc_id=f"DOC-{file_path.stem}",
                        title=file_path.stem.replace("_", " ").title(),
                        equipment_category=cat,
                    )
                    all_chunks.extend(chunks)
            if all_chunks:
                self.add_chunks(all_chunks)
                logger.info("Auto-indexed %d manual chunks from %s", len(all_chunks), manuals_dir)
        except Exception as e:
            logger.warning("Could not auto-load existing manuals: %s", e)

    def _init_backend(self) -> None:
        """Attempt initializing ChromaDB; fall back to resilient TF-IDF/cosine index if needed."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self.backend_type = "chromadb"
            logger.info("ChromaDB vector store initialized at %s", self.persist_dir)
        except Exception as e:
            logger.warning("ChromaDB initialization failed (%s). Using resilient semantic fallback.", e)
            self.backend_type = "resilient_semantic_tfidf"

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Add text chunks with metadata to vector store."""
        if not chunks:
            return 0

        # Store in local document catalog
        for c in chunks:
            self.documents[c["id"]] = c

        # 1. Store in ChromaDB if available
        if self.backend_type == "chromadb" and self.collection is not None:
            try:
                ids = [c["id"] for c in chunks]
                documents = [c["content"] for c in chunks]
                metadatas = [
                    {
                        "doc_id": c.get("doc_id", ""),
                        "title": c.get("title", ""),
                        "filename": c.get("filename", ""),
                        "equipment_category": c.get("equipment_category", "general_av"),
                        "page_number": int(c.get("page_number", 1)),
                        "chunk_index": int(c.get("chunk_index", 0)),
                    }
                    for c in chunks
                ]
                self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            except Exception as e:
                logger.error("Error upserting to ChromaDB: %s. Relying on semantic index.", e)

        # 2. Update TF-IDF semantic index
        self._rebuild_tfidf_index()
        return len(chunks)

    def _rebuild_tfidf_index(self) -> None:
        """Build or update TF-IDF index across all active documents."""
        if not self.documents:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            texts = [doc["content"] for doc in self.documents.values()]
            self.tfidf_vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", max_features=5000)
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        except Exception as e:
            logger.warning("Could not build TF-IDF index: %s", e)

    def query(
        self,
        query_text: str,
        equipment_category: Optional[str] = None,
        top_k: int = 3,
        distance_threshold: float = 0.85,
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks with source attribution.

        Returns list of matching chunks with similarity score and metadata.
        """
        if not query_text or not query_text.strip():
            return []

        clean_query = query_text.strip()

        # Try ChromaDB query
        if self.backend_type == "chromadb" and self.collection is not None:
            try:
                where_filter = None
                if equipment_category and equipment_category != "general_av":
                    where_filter = {"equipment_category": equipment_category}

                results = self.collection.query(
                    query_texts=[clean_query],
                    n_results=top_k * 2,
                    where=where_filter,
                )

                matches: List[Dict[str, Any]] = []
                if results and results.get("ids") and len(results["ids"][0]) > 0:
                    ids = results["ids"][0]
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

                    for chunk_id, doc_text, meta, dist in zip(ids, docs, metas, distances):
                        if dist is not None and dist > distance_threshold:
                            continue  # Below threshold
                        score = round(1.0 - (dist if dist is not None else 0.0), 3)
                        matches.append({
                            "id": chunk_id,
                            "content": doc_text,
                            "title": meta.get("title", "Approved AV Manual"),
                            "filename": meta.get("filename", "Manual"),
                            "equipment_category": meta.get("equipment_category", "general_av"),
                            "page_number": meta.get("page_number", 1),
                            "similarity_score": score,
                            "source_attribution": f"{meta.get('title', 'Manual')} (Page {meta.get('page_number', 1)})",
                        })

                if matches:
                    return matches[:top_k]
            except Exception as e:
                logger.warning("ChromaDB query fallback triggered: %s", e)

        # Resilient Fallback: TF-IDF Cosine Similarity
        return self._query_tfidf(clean_query, equipment_category=equipment_category, top_k=top_k)

    def _query_tfidf(
        self,
        query_text: str,
        equipment_category: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Fallback retrieval using cosine similarity."""
        if not self.documents or self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            return []

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = self.tfidf_vectorizer.transform([query_text])
            sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

            doc_list = list(self.documents.values())
            scored = []
            for idx, score in enumerate(sims):
                doc = doc_list[idx]
                if equipment_category and equipment_category != "general_av":
                    if doc.get("equipment_category") not in [equipment_category, "general_av"]:
                        continue
                if score > 0.05:  # Minimum relevance floor
                    scored.append((score, doc))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, doc in scored[:top_k]:
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "title": doc.get("title", "Manual"),
                    "filename": doc.get("filename", "Manual"),
                    "equipment_category": doc.get("equipment_category", "general_av"),
                    "page_number": doc.get("page_number", 1),
                    "similarity_score": round(float(score), 3),
                    "source_attribution": f"{doc.get('title', 'Manual')} (Page {doc.get('page_number', 1)})",
                })
            return results
        except Exception as e:
            logger.error("TF-IDF query failed: %s", e)
            return []

    def count(self) -> int:
        """Return total count of indexed chunks."""
        if self.collection is not None:
            try:
                return self.collection.count()
            except Exception:
                pass
        return len(self.documents)

    def get_status(self) -> Dict[str, Any]:
        """Telemetry details for admin view."""
        count = len(self.documents)
        if self.collection is not None:
            try:
                count = self.collection.count()
            except Exception:
                pass
        return {
            "backend": self.backend_type,
            "total_chunks": count,
            "persist_directory": str(self.persist_dir),
            "collection_name": self.collection_name,
        }

    def clear(self) -> None:
        """Reset vector store."""
        self.documents.clear()
        if self.collection is not None:
            try:
                self.chroma_client.delete_collection(self.collection_name)
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass
        self.tfidf_matrix = None
        self.tfidf_vectorizer = None


# Global singleton instance
vector_store = AVVectorStore()
