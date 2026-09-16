"""Vector embedding and similarity calculation engine."""


import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingEngine:
    """Semantic vector engine for fast similarity matching."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True
        )
        self.fitted = False
        self.corpus_texts: list[str] = []
        self.tfidf_matrix = None

    def fit(self, texts: list[str]):
        """Fits vectorizer on the corpus."""
        if not texts:
            return
        self.corpus_texts = texts
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self.fitted = True

    def find_top_k(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        """Returns top k matching indices and cosine similarity scores."""
        if not self.fitted or not self.corpus_texts:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        top_indices = np.argsort(similarities)[::-1][:k]
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            results.append((int(idx), score))
        return results
