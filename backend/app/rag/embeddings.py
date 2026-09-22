"""
Lightweight vector index for closed-case similarity retrieval.

Uses TF-IDF + cosine similarity over the 5,565 closed cases.
No external vector database required — reproducible, deterministic.
sklearn is already installed.

Index is built once at startup and cached in memory.
"""

from __future__ import annotations

import logging
import pickle
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).parent.parent.parent / "fraud_cases_index.pkl"


def _build_document_text(case: dict) -> str:
    """
    Convert a closed-case record to a searchable text string.
    Uses only actual columns from closed_cases_history.csv.
    """
    parts = [
        f"outcome:{case.get('outcome', '')}",
        f"pattern:{case.get('pattern', '')}",
        f"exposure:{case.get('exposure_usd', '')}",
        f"n_txns:{case.get('n_txns', '')}",
        case.get("analyst_notes", "") or "",
        f"card:{case.get('card_id', '')}",
        f"customer:{case.get('customer_id', '')}",
        f"actions:{case.get('actions_taken', '')}",
    ]
    return " ".join(str(p) for p in parts if p)


class CaseSimilarityIndex:
    """
    TF-IDF vector index over closed cases.

    Similarity is computed from actual case fields — not LLM inference.
    """

    def __init__(self) -> None:
        self._cases: list[dict] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None    # sparse (n_cases × features)
        self._built = False

    def build(self, cases: list[dict]) -> None:
        """Build the index from the closed-cases list."""
        if not cases:
            logger.warning("CaseSimilarityIndex.build called with empty case list")
            return
        self._cases = cases
        docs = [_build_document_text(c) for c in cases]
        self._vectorizer = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            min_df=2,
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(docs)
        self._built = True
        logger.info("CaseSimilarityIndex built: %d cases, %d features",
                    len(cases), self._matrix.shape[1])

    def save(self) -> None:
        if not self._built:
            return
        with open(_CACHE_PATH, "wb") as f:
            pickle.dump({
                "cases": self._cases,
                "vectorizer": self._vectorizer,
                "matrix": self._matrix,
            }, f)
        logger.debug("Index saved to %s", _CACHE_PATH)

    def load(self) -> bool:
        if not _CACHE_PATH.exists():
            return False
        try:
            with open(_CACHE_PATH, "rb") as f:
                data = pickle.load(f)
            self._cases = data["cases"]
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            self._built = True
            logger.info("CaseSimilarityIndex loaded from cache: %d cases", len(self._cases))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Index load failed: %s — will rebuild", exc)
            return False

    def find_similar(
        self,
        query_case: dict,
        top_k: int = 5,
        min_score: float = 0.05,
    ) -> list[dict[str, Any]]:
        """
        Return the top-k most similar closed cases to query_case.

        Each result contains:
          case_id, why_similar, matching_evidence, historical_outcome, relevance

        Nothing is fabricated — similarity is cosine distance on TF-IDF features.
        """
        if not self._built or self._vectorizer is None or self._matrix is None:
            return []

        query_text = _build_document_text(query_case)
        query_vec = self._vectorizer.transform([query_text])
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        # Get top-k indices, excluding the query case itself
        query_id = query_case.get("case_id", "")
        top_idx = np.argsort(scores)[::-1]

        results = []
        for idx in top_idx:
            if len(results) >= top_k:
                break
            score = float(scores[idx])
            if score < min_score:
                break
            case = self._cases[idx]
            if case.get("case_id") == query_id:
                continue

            # Determine which fields contributed to similarity
            matching = []
            if query_case.get("pattern") and case.get("pattern") == query_case.get("pattern"):
                matching.append(f"same pattern: {case.get('pattern')}")
            if query_case.get("customer_id") == case.get("customer_id"):
                matching.append(f"same customer: {case.get('customer_id')}")
            if query_case.get("card_id") == case.get("card_id"):
                matching.append(f"same card: {case.get('card_id')}")
            try:
                q_exp = float(query_case.get("exposure_usd") or 0)
                c_exp = float(case.get("exposure_usd") or 0)
                if q_exp > 0 and c_exp > 0 and abs(q_exp - c_exp) / max(q_exp, c_exp) < 0.5:
                    matching.append(f"similar exposure: ${c_exp}")
            except (ValueError, TypeError):
                pass
            if not matching:
                matching.append("document similarity (text/pattern/notes)")

            results.append({
                "case_id": case.get("case_id", ""),
                "outcome": case.get("outcome", ""),
                "pattern": case.get("pattern", ""),
                "exposure_usd": case.get("exposure_usd", ""),
                "n_txns": case.get("n_txns", ""),
                "analyst_notes": (case.get("analyst_notes") or "")[:300],
                "why_similar": "; ".join(matching),
                "matching_evidence": matching,
                "historical_outcome": case.get("outcome", ""),
                "relevance": round(score, 4),
            })

        return results


# ── Module-level singleton ────────────────────────────────────────────────────

_index_instance: CaseSimilarityIndex | None = None


def get_case_index() -> CaseSimilarityIndex:
    """Return the shared index, building it if necessary."""
    global _index_instance
    if _index_instance is None:
        _index_instance = CaseSimilarityIndex()
    return _index_instance


def ensure_index_built(cases: list[dict]) -> CaseSimilarityIndex:
    """Build or load the index. Call once at startup."""
    idx = get_case_index()
    if not idx._built:
        if not idx.load():
            idx.build(cases)
            idx.save()
    return idx
