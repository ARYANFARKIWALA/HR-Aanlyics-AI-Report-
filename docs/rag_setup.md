# RAG Knowledge Base Architecture & Setup (Module 5)

## 1. Overview

The RAG (Retrieval-Augmented Generation) knowledge base connects unstructured organizational documents (HR handbooks, compensation guidelines, leave policies, effective dating standards) to structured database metadata.

```text
[HR Guidelines & Policies] ──► [Document Ingestion] ──► [Chunking & Embeddings] ──► [Vector DB / TF-IDF]
                                                                                            │
[User Natural Language Query] ──────────────────────────────────────────────────────────────┴──► [Context Retrieval]
                                                                                                        │
                                                                                                        ▼
                                                                                               [Text-to-SQL Prompt]
```

---

## 2. Multi-Tenancy & Access-Controlled Retrieval

Every indexed document and chunk tracks:
- `organization_id`: Strictly isolates queries per tenant.
- `document_type`: "Policy", "SchemaRule", "SQLTemplate", "BusinessDefinition".
- `access_roles`: Ensures low-privilege roles cannot retrieve confidential executive policy text.

---

## 3. Supported Vector Backends
1. **PostgreSQL pgvector**: Production standard for enterprise semantic similarity search.
2. **Deterministic Hybrid TF-IDF**: Built-in offline fallback requiring zero external API keys.
