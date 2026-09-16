"""RAG Retrieval Engine for both HR Policies and Enterprise SQL Templates."""

from typing import Any

from sqlalchemy.orm import Session

from ai.model import llm_client

from .embeddings import EmbeddingEngine
from .ingestion import DocumentIngester, PolicyDocument


class RAGRetriever:
    """Manages indexing and semantic search across policies and SQL repository templates."""

    def __init__(self):
        self.policy_engine = EmbeddingEngine()
        self.sql_engine = EmbeddingEngine()
        self.policies: list[PolicyDocument] = []
        self.sql_docs: list[dict[str, Any]] = []
        self._initialized = False

    def initialize(self, db_session: Session | None = None):
        """Builds index matrices from policies and database SQL templates."""
        # Index Policies
        self.policies = DocumentIngester.get_all_policies()
        policy_texts = [f"{p.title}\n{p.category}\n{p.content}" for p in self.policies]
        self.policy_engine.fit(policy_texts)

        # Index SQL Repository if session provided
        if db_session:
            self.reload_sql_repository(db_session)

        self._initialized = True

    def reload_sql_repository(self, db_session: Session):
        """Refreshes SQL repository vector index from the database."""
        self.sql_docs = DocumentIngester.get_sql_repository_documents(db_session)
        sql_texts = [doc["composite_text"] for doc in self.sql_docs]
        if sql_texts:
            self.sql_engine.fit(sql_texts)

    def search_sql_templates(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Finds closest matching verified enterprise SQL queries."""
        if not self.sql_docs:
            return []
        matches = self.sql_engine.find_top_k(query, k=top_k)
        results = []
        for idx, score in matches:
            if idx < len(self.sql_docs):
                item = self.sql_docs[idx].copy()
                item["similarity_score"] = round(score, 3)
                results.append(item)
        return results

    def search_policies(self, query: str, top_k: int = 2) -> list[dict[str, Any]]:
        """Retrieves matching HR policies."""
        matches = self.policy_engine.find_top_k(query, k=top_k)
        results = []
        for idx, score in matches:
            if idx < len(self.policies):
                doc = self.policies[idx]
                results.append({
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "category": doc.category,
                    "content": doc.content,
                    "similarity_score": round(score, 3)
                })
        return results

    def answer_policy_question(self, query: str) -> dict[str, Any]:
        """Answers an HR policy question using retrieved context and LLM."""
        matched_policies = self.search_policies(query, top_k=2)
        if not matched_policies:
            return {
                "answer": "No relevant company policy documents were found matching your inquiry.",
                "sources": []
            }

        context_blocks = "\n\n".join(
            [f"--- Policy: {p['title']} ---\n{p['content']}" for p in matched_policies]
        )

        prompt = f"""Based strictly on the following HR policy documentation, answer the user's question accurately.
If the information is not contained in the policies, explicitly state that.

POLICIES:
{context_blocks}

QUESTION:
{query}

ANSWER:"""

        answer = llm_client.generate(prompt, system_instruction="You are a helpful and authoritative HR Policy Assistant.")
        return {
            "answer": answer,
            "sources": matched_policies
        }


rag_retriever = RAGRetriever()
