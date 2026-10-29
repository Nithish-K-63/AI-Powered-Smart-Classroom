"""Knowledge Base and RAG Retrieval Engine for Classroom AV Troubleshooting.

Builds searchable knowledge documents from the 5,000 historical troubleshooting records.
Supports:
1. Semantic dense vector retrieval via FAISS and sentence-embeddings.
2. High-performance Keyword retrieval via Scikit-Learn TF-IDF & Cosine Similarity as a guaranteed fallback.
3. Strict empirical grounding: Never invents manual citations or claims examples are manufacturer manuals.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import settings
from .dataset_loader import AVDatasetLoader

logger = logging.getLogger(__name__)

# Explicit attribution string ensuring compliance with Requirement 7
EMPIRICAL_DATASET_ATTRIBUTION = (
    "Empirical historical classroom incident record (Internal AV Log Dataset) - "
    "Not official manufacturer manual instructions."
)


class KnowledgeRetriever:
    """RAG Knowledge Base indexing historical troubleshooting fixes and procedures.

    Provides dual-strategy retrieval:
    - Semantic retrieval (FAISS + Sentence-Transformers)
    - Keyword-based retrieval (TF-IDF + Cosine Similarity)
    """

    def __init__(
        self,
        loader: Optional[AVDatasetLoader] = None,
        force_backend: Optional[str] = None,
    ):
        self.loader = loader or AVDatasetLoader()
        self.force_backend = force_backend
        self.documents: List[Dict[str, Any]] = []
        self.doc_texts: List[str] = []

        # Keyword retriever components
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None

        # Semantic FAISS components
        self.embedding_model = None
        self.faiss_index = None
        self.backend_used: str = "tfidf"
        self.semantic_available: bool = False

        self._build_knowledge_base()

    def _build_knowledge_base(self) -> None:
        """Extract and index deduplicated knowledge articles from the historical CSV."""
        df = self.loader.load_data(validate=False)

        # 1. Build Incident-level Troubleshooting Chunks from CSV columns:
        # device_type, model, symptom, power_status, input_source, cable_status, fix_step
        grouped = (
            df.groupby([
                "device_type",
                "model",
                "symptom",
                "power_status",
                "input_source",
                "cable_status",
                "fix_step",
            ])
            .agg(
                total_cases=("resolved", "count"),
                resolved_cases=("resolved", lambda s: (s == "yes").sum()),
                escalated_cases=("escalated", lambda s: (s == "yes").sum()),
            )
            .reset_index()
        )

        for _, row in grouped.iterrows():
            total = int(row["total_cases"])
            resolved = int(row["resolved_cases"])
            escalated = int(row["escalated_cases"])
            res_rate = round((resolved / total) * 100, 1)

            text = (
                f"Historical Incident | Device: {row['device_type']} | Model: {row['model']} | "
                f"Symptom: {row['symptom']} | Power Status: {row['power_status']} | "
                f"Input Source: {row['input_source']} | Cable: {row['cable_status']} | "
                f"Empirical Fix Step: {row['fix_step']} | "
                f"Historical Outcome: {resolved}/{total} resolved ({res_rate}%), {escalated} escalated"
            )

            doc = {
                "doc_id": len(self.documents),
                "type": "troubleshooting_procedure",
                "device_type": row["device_type"],
                "model": row["model"],
                "symptom": row["symptom"],
                "power_status": row["power_status"],
                "input_source": row["input_source"],
                "cable_status": row["cable_status"],
                "fix_step": row["fix_step"],
                "historical_total": total,
                "resolution_rate_pct": res_rate,
                "escalated_count": escalated,
                "text": text,
                "attribution": EMPIRICAL_DATASET_ATTRIBUTION,
            }
            self.documents.append(doc)
            self.doc_texts.append(text)

        # 2. Build High-Level Symptom Master Summary Guides
        symptom_groups = (
            df.groupby(["device_type", "symptom"])
            .agg(
                total_incidents=("resolved", "count"),
                resolved_count=("resolved", lambda s: (s == "yes").sum()),
            )
            .reset_index()
        )

        for _, s_row in symptom_groups.iterrows():
            dev = s_row["device_type"]
            sym = s_row["symptom"]
            tot = int(s_row["total_incidents"])
            res = int(s_row["resolved_count"])
            res_pct = round((res / tot) * 100, 1)

            # Extract top 3 historical fixes for this symptom
            subset = df[(df["device_type"] == dev) & (df["symptom"] == sym)]
            top_fixes = subset["fix_step"].value_counts().head(3).index.tolist()
            fixes_str = "; ".join(top_fixes)

            text = (
                f"Historical Symptom Summary: {dev.upper()} experiencing '{sym}'. "
                f"Total classroom incidents: {tot}. Baseline resolution rate: {res_pct}%. "
                f"Historical resolution actions: {fixes_str}."
            )

            doc = {
                "doc_id": len(self.documents),
                "type": "master_symptom_card",
                "device_type": dev,
                "model": "All Models",
                "symptom": sym,
                "power_status": "Any",
                "input_source": "Any",
                "cable_status": "Any",
                "fix_step": top_fixes[0] if top_fixes else "",
                "historical_total": tot,
                "resolution_rate_pct": res_pct,
                "escalated_count": tot - res,
                "text": text,
                "attribution": EMPIRICAL_DATASET_ATTRIBUTION,
            }
            self.documents.append(doc)
            self.doc_texts.append(text)

        logger.info("Compiled %d empirical knowledge entries from CSV dataset.", len(self.documents))

        # 3. Initialize Keyword Retriever (TF-IDF keyword index - Guaranteed Fallback)
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            max_features=5000,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.doc_texts)

        # 4. Attempt Semantic FAISS Index Initialization if requested
        requested_backend = self.force_backend or settings.RETRIEVER_BACKEND
        if requested_backend in ("faiss", "semantic"):
            self._try_init_faiss_semantic()
        elif requested_backend == "auto":
            # On non-Windows platforms or when explicitly configured, try FAISS
            if sys.platform != "win32":
                self._try_init_faiss_semantic()
            else:
                self.backend_used = "tfidf"
                logger.info("Running on Windows with 'auto' backend: Defaulted to instant TF-IDF keyword retriever.")
        else:
            self.backend_used = "tfidf"
            logger.info("Retriever backend set to TF-IDF keyword retriever.")

    def _try_init_faiss_semantic(self) -> bool:
        """Attempt to load FAISS and sentence-embedding model."""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformers embedding model '%s'...", settings.RAG_EMBEDDING_MODEL)
            self.embedding_model = SentenceTransformer(settings.RAG_EMBEDDING_MODEL)

            # Sample embeddings to build FAISS index
            sample_embeddings = self.embedding_model.encode(self.doc_texts, show_progress_bar=False, normalize_embeddings=True)
            dim = sample_embeddings.shape[1]

            index = faiss.IndexFlatIP(dim)
            index.add(np.array(sample_embeddings, dtype=np.float32))
            self.faiss_index = index
            self.backend_used = "faiss_semantic"
            self.semantic_available = True
            logger.info("Semantic FAISS index successfully created with %d vectors", index.ntotal)
            return True
        except Exception as e:
            logger.warning(
                "FAISS or SentenceTransformer initialization failed/bypassed: %s. "
                "Activating Scikit-Learn TF-IDF keyword retrieval fallback.",
                e,
            )
            self.backend_used = "tfidf"
            self.semantic_available = False
            return False

    def retrieve(
        self,
        query: str,
        device_type: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """Retrieve the most relevant troubleshooting documents for a given query.

        Handles:
        - Empty or whitespace query gracefully.
        - Semantic FAISS retrieval when active.
        - Keyword TF-IDF fallback when FAISS/embeddings are inactive or return low similarity.
        - Explicit attribution metadata attached to every retrieved card.
        """
        if not self.documents:
            return []

        cleaned_query = (query or "").strip()
        # Handle empty query gracefully
        if not cleaned_query:
            logger.debug("Empty query passed to retrieve(). Returning top general symptom cards.")
            return self._get_default_fallback_cards(device_type, top_k)

        # Incorporate device_type into query for enriched relevance
        query_text = cleaned_query
        if device_type and device_type.lower() not in query_text.lower():
            query_text = f"{device_type} {query_text}"

        # 1. Try Semantic FAISS Retrieval if active
        if self.backend_used == "faiss_semantic" and self.faiss_index is not None and self.embedding_model is not None:
            try:
                query_vec = self.embedding_model.encode([query_text], normalize_embeddings=True)
                distances, indices = self.faiss_index.search(
                    np.array(query_vec, dtype=np.float32),
                    min(top_k * 4, len(self.documents)),
                )
                matched_pairs = list(zip(indices[0], distances[0]))
                results = self._filter_and_format_results(matched_pairs, device_type, top_k)
                if results:
                    return results
            except Exception as e:
                logger.warning("Error during FAISS search: %s. Falling back to keyword search.", e)

        # 2. Keyword-based Retrieval Fallback (TF-IDF Cosine Similarity)
        return self._keyword_retrieve(query_text, device_type=device_type, top_k=top_k)

    def _keyword_retrieve(
        self,
        query_text: str,
        device_type: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """Execute keyword-based search using TF-IDF and cosine similarity."""
        if self.vectorizer is None or self.tfidf_matrix is None:
            return self._get_default_fallback_cards(device_type, top_k)

        query_vec = self.vectorizer.transform([query_text])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Check if any matches have non-zero similarity
        max_sim = float(np.max(sims)) if len(sims) > 0 else 0.0
        if max_sim <= 0.0:
            logger.debug("No keyword match found for '%s'. Providing broad fallback cards.", query_text)
            return self._get_default_fallback_cards(device_type, top_k)

        top_indices = np.argsort(sims)[::-1][: top_k * 4]
        matched_pairs = [(idx, float(sims[idx])) for idx in top_indices if sims[idx] > 0.0]

        results = self._filter_and_format_results(matched_pairs, device_type, top_k)
        if not results:
            return self._get_default_fallback_cards(device_type, top_k)
        return results

    def _filter_and_format_results(
        self,
        matched_pairs: List[Tuple[int, float]],
        device_type: Optional[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Filter by device type, deduplicate, and attach empirical attribution."""
        results = []
        seen_fixes = set()

        for idx, score in matched_pairs:
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[idx].copy()

            # Apply device filter if requested
            if device_type:
                doc_dev = doc.get("device_type", "").lower()
                req_dev = device_type.lower()
                if doc_dev != req_dev and doc_dev != "all models" and doc_dev != "all":
                    continue

            fix = doc.get("fix_step", "").strip()
            if fix in seen_fixes:
                continue
            seen_fixes.add(fix)

            doc["similarity_score"] = round(float(score), 4)
            doc["retrieval_backend"] = self.backend_used
            doc["attribution"] = EMPIRICAL_DATASET_ATTRIBUTION
            results.append(doc)

            if len(results) >= top_k:
                break

        return results

    def _get_default_fallback_cards(
        self,
        device_type: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """Return high-level standard symptom cards when a query is empty or out-of-domain."""
        cards = []
        for doc in self.documents:
            if doc.get("type") == "master_symptom_card":
                if device_type and doc.get("device_type", "").lower() != device_type.lower():
                    continue
                d = doc.copy()
                d["similarity_score"] = 0.0
                d["retrieval_backend"] = f"{self.backend_used}_fallback"
                d["attribution"] = EMPIRICAL_DATASET_ATTRIBUTION
                cards.append(d)
                if len(cards) >= top_k:
                    break
        return cards

    def get_status(self) -> Dict[str, Any]:
        """Return status information for the retrieval engine."""
        return {
            "backend_used": self.backend_used,
            "semantic_available": self.semantic_available,
            "total_documents_indexed": len(self.documents),
            "faiss_active": self.faiss_index is not None,
            "embedding_model": settings.RAG_EMBEDDING_MODEL if self.semantic_available else None,
            "keyword_vector_dimension": self.tfidf_matrix.shape[1] if self.tfidf_matrix is not None else 0,
        }


# Global knowledge retriever singleton
retriever = KnowledgeRetriever()
