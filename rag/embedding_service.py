"""Module 5: Embedding Service.

Generates dense vector embeddings for knowledge text chunks.
Supports:
- SentenceTransformers (if installed and configured)
- Deterministic semantic dense projection (lightweight, zero-dependency fallback)
Produces normalized float vectors suitable for cosine similarity and pgvector.
"""

import hashlib
import math
import os
import re

EMBEDDING_DIM = 128


class EmbeddingService:
    """Configurable embedding generator."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._st_model = None
        self._initialize_model()

    def _initialize_model(self):
        """Attempts to load sentence_transformers if available."""
        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer(self.model_name)
        except Exception:
            self._st_model = None

    def generate_embedding(self, text: str) -> list[float]:
        """Generates a normalized dense embedding vector for a single text string."""
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM

        if self._st_model:
            try:
                vec = self._st_model.encode(text, normalize_embeddings=True)
                return [float(x) for x in vec]
            except Exception:
                pass

        # Deterministic semantic projection fallback
        return self._dense_hash_projection(text, dim=EMBEDDING_DIM)

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates embeddings for a batch of text strings."""
        return [self.generate_embedding(t) for t in texts]

    @classmethod
    def _dense_hash_projection(cls, text: str, dim: int = 128) -> list[float]:
        """Generates a unit-normalized dense semantic vector using n-gram feature hashing."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = clean.split()

        vector = [0.0] * dim

        # 1. Unigram & Bigram hashing
        for i, token in enumerate(tokens):
            # Unigram
            h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dim
            vector[h1] += 1.0

            # Bigram
            if i > 0:
                bigram = f"{tokens[i-1]}_{token}"
                h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16) % dim
                vector[h2] += 1.5

        # 2. L2 Normalization
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0.0:
            return [0.0] * dim
        return [round(x / norm, 6) for x in vector]

    @classmethod
    def cosine_similarity(cls, vec_a: list[float], vec_b: list[float]) -> float:
        """Computes cosine similarity between two unit vectors."""
        if not vec_a or not vec_b:
            return 0.0
        # If already unit vectors, dot product equals cosine similarity
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        return max(0.0, min(1.0, float(dot)))
