# Preserving and Reusing Existing Institutional SQL Knowledge

A core architectural philosophy of the **HR Analytics AI Report Builder** is that enterprise reporting intelligence must **preserve and reuse proven organizational SQL knowledge** rather than attempting to generate raw queries from scratch using generic LLMs without organizational context.

---

## 1. The Fallacy of Generic Text-to-SQL

Generic Text-to-SQL systems often fail in production enterprise HR environments due to:
1. **Lack of Business Context**: A generic LLM does not know whether "headcount" requires filtering on `status = 'Active'`, whether contractor staff should be excluded, or what effective-dating logic applies (`is_current = 1`).
2. **Hallucinated Joins & Schema Entities**: Without historical query patterns, LLMs invent table joins or produce Cartesian products on complex schemas.
3. **Loss of Decades of BI Engineering**: Organizations spend years refining business-critical reports, regulatory compliance queries, and financial reconciliation scripts. Discarding this institutional knowledge forces organizations to reinvent wheels and introduces compliance risks.

---

## 2. Institutional Knowledge Preservation Architecture

The platform preserves and leverages existing SQL reporting assets through a multi-tiered knowledge lifecycle:

```text
[Historical Enterprise SQL Reports]
(Decades of approved BI queries, join graphs, effective-dating logic)
                         │
                         ▼
             [Module 2: SQL Repository Catalog]
         (Parsed AST, Lineage, Business Rule Extraction)
                         │
                         ▼
             [Module 5: Hybrid Policy RAG]
       (Dense Vector Embeddings + Metadata Tagging)
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
[Natural Language Prompt]     [Relevant Approved SQL Templates]
        │                                 │
        └────────────────┬────────────────┘
                         ▼
        [Module 6: Knowledge-Augmented Text-to-SQL]
(Reuses proven join patterns, filters, and business definitions)
                         │
                         ▼
           [Dialect Transpilation & Safety Gate]
(PostgreSQL, SQLite, MySQL, SQL Server, Oracle without hallucination)
```

---

## 3. How Approved SQL Patterns are Reused in Practice

When a user asks:
> *"Show monthly employee attrition by department for 2026."*

1. **Semantic Match**: Module 5 searches the vector database and identifies existing approved report `SQLRPT-ATTR-01` (*"Departmental Attrition & Voluntary Turnover Analysis"*).
2. **Pattern Ingestion**: The system extracts:
   - Proven join graph: `employees INNER JOIN departments ON employees.department_id = departments.id`.
   - Organizational attrition rule: `status = 'Terminated'` with temporal bounds on `termination_date`.
   - Dimension definitions: `departments.name` and month formatting `strftime('%Y-%m', termination_date)`.
3. **Query Adaptation**: Module 6 adapts the approved query to target year 2026 and target engine dialect, maintaining 100% adherence to verified business rules.
4. **Result**: Zero schema hallucinations, zero unexpected Cartesian products, and 100% mathematical consistency with existing organizational BI dashboards.
