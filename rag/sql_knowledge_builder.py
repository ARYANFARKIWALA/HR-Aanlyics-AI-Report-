"""Module 2: RAG-Ready SQL Knowledge Document Builder.

Transforms approved enterprise SQL reports and their extracted metadata
into structured, LlamaIndex-compatible knowledge documents ready for Module 5 RAG indexing.
Includes permission-aware metadata (organization_id, database_id, security_scope).
"""

import json
from typing import Any

from backend.database.models_repo import SQLReport, SQLReportMetadata


class SQLKnowledgeDocument:
    """Represents a structured knowledge document suitable for vector indexing and LLM context."""

    def __init__(
        self,
        doc_id: str,
        text_content: str,
        metadata: dict[str, Any],
        report_code: str,
        report_name: str,
        category: str,
        database_id: str
    ):
        self.doc_id = doc_id
        self.text_content = text_content
        self.metadata = metadata
        self.report_code = report_code
        self.report_name = report_name
        self.category = category
        self.database_id = database_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text": self.text_content,
            "metadata": self.metadata,
            "report_code": self.report_code,
            "report_name": self.report_name,
            "category": self.category,
            "database_id": self.database_id,
        }

    def to_llamaindex_document(self) -> Any:
        """Converts to a LlamaIndex Document if llama_index is installed."""
        try:
            from llama_index.core import Document
            return Document(text=self.text_content, extra_info=self.metadata, id_=self.doc_id)
        except ImportError:
            # Return dict representation if LlamaIndex is not yet installed
            return self.to_dict()


class SQLKnowledgeBuilder:
    """Builds standardized knowledge documents from approved SQL reports."""

    @classmethod
    def build_knowledge_document(
        cls,
        report: SQLReport,
        meta: SQLReportMetadata | None = None
    ) -> SQLKnowledgeDocument:
        """Transforms an approved SQLReport record into a comprehensive RAG knowledge document."""
        # Unpack metadata JSON strings
        tables = json.loads(meta.tables_json) if meta and meta.tables_json else []
        columns = json.loads(meta.columns_json) if meta and meta.columns_json else []
        joins = json.loads(meta.joins_json) if meta and meta.joins_json else []
        json.loads(meta.filters_json) if meta and meta.filters_json else []
        aggregations = json.loads(meta.aggregations_json) if meta and meta.aggregations_json else []
        json.loads(meta.date_conditions_json) if meta and meta.date_conditions_json else []
        eff_dating = json.loads(meta.effective_dating_details) if meta and meta.effective_dating_details else []
        sec_filters = json.loads(meta.security_filters_details) if meta and meta.security_filters_details else []
        biz_logic = json.loads(meta.business_logic_details) if meta and meta.business_logic_details else []

        parameters = [
            f"{p.parameter_name} ({p.parameter_type})"
            for p in (report.parameters or [])
        ]

        join_lines = []
        for j in joins:
            join_lines.append(f"  - {j.get('left_table')} {j.get('join_type')} {j.get('right_table')} ON {j.get('join_condition')}")
        joins_str = "\n".join(join_lines) if join_lines else "None (Single table query)"

        agg_str = ", ".join([f"{a.get('function')}({a.get('column')})" for a in aggregations]) or "None"

        # Construct comprehensive markdown knowledge text
        text_blocks = [
            f"# Enterprise HR SQL Report: {report.report_name}",
            f"**Report Code:** {report.report_code}",
            f"**Organization:** {report.organization_id} | **Target Database:** {report.database_id}",
            f"**Category:** {report.category} | **Status:** {report.status} | **Version:** v{report.version}",
            "",
            "## Business Purpose & Description",
            report.business_purpose or report.description or "No business purpose specified.",
            "",
            "## Data Lineage & Schema Relationships",
            f"- **Tables Referenced:** {', '.join(tables) or 'None'}",
            f"- **Projection Columns:** {', '.join(columns[:15])}{'...' if len(columns) > 15 else ''}",
            "- **Join Graph:**",
            joins_str,
            "",
            "## Business Rules & Metrics",
            f"- **Aggregations & Metrics:** {agg_str}",
            f"- **Effective Dating Logic Applied:** {'YES' if (meta and meta.uses_effective_dating) else 'NO'}",
        ]

        if eff_dating:
            text_blocks.append(f"  * Details: {'; '.join(eff_dating)}")

        text_blocks.extend([
            f"- **Security Filters Present:** {'YES' if (meta and meta.uses_security_filter) else 'NO'}",
        ])
        if sec_filters:
            text_blocks.append(f"  * Security Columns: {', '.join(sec_filters)}")

        if biz_logic:
            text_blocks.append(f"- **Advanced Business Logic:** {', '.join(biz_logic)}")

        if parameters:
            text_blocks.append(f"- **Query Parameters:** {', '.join(parameters)}")

        text_blocks.extend([
            f"- **Calculated Complexity:** {meta.complexity_level if meta else 'LOW'} (Score: {meta.complexity_score if meta else 1.0})",
            "",
            "## Verified Enterprise SQL Query",
            "```sql",
            report.sql_query.strip(),
            "```",
        ])

        full_text = "\n".join(text_blocks)

        # Build permission-aware metadata dictionary for Module 5 RAG filtering
        metadata = {
            "report_id": report.id,
            "report_code": report.report_code,
            "organization_id": report.organization_id,
            "database_id": report.database_id,
            "category": report.category,
            "status": report.status,
            "version": report.version,
            "tables": tables,
            "uses_effective_dating": meta.uses_effective_dating if meta else False,
            "uses_security_filter": meta.uses_security_filter if meta else False,
            "complexity_level": meta.complexity_level if meta else "LOW",
            "security_scope": sec_filters,
        }

        return SQLKnowledgeDocument(
            doc_id=f"KNOW-{report.report_code}",
            text_content=full_text,
            metadata=metadata,
            report_code=report.report_code,
            report_name=report.report_name,
            category=report.category,
            database_id=report.database_id
        )
