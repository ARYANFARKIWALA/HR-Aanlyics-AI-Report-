"""Module 3: RAG-Ready Schema Knowledge Document Builder.

Transforms enriched HR database schemas, semantic mappings, and relationships
into structured, LlamaIndex-compatible knowledge documents ready for Module 5 RAG
and Module 6 AI Text-to-SQL generation.
Supports role-based redaction of sensitive columns (e.g. FINANCIAL, PERSONAL_IDENTIFIER).
"""

from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_schema import SchemaRelationship, SchemaTable


class SchemaKnowledgeDocument:
    """Represents a structured schema knowledge document for vector indexing and LLM prompt grounding."""

    def __init__(
        self,
        doc_id: str,
        text_content: str,
        metadata: dict[str, Any],
        doc_type: str,
        database_id: str,
        table_name: str | None = None,
        business_entity: str | None = None
    ):
        self.doc_id = doc_id
        self.text_content = text_content
        self.metadata = metadata
        self.doc_type = doc_type
        self.database_id = database_id
        self.table_name = table_name
        self.business_entity = business_entity

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text": self.text_content,
            "metadata": self.metadata,
            "doc_type": self.doc_type,
            "database_id": self.database_id,
            "table_name": self.table_name,
            "business_entity": self.business_entity,
        }

    def to_llamaindex_document(self) -> Any:
        """Converts to a LlamaIndex Document object if llama_index is installed."""
        try:
            from llama_index.core import Document
            return Document(text=self.text_content, extra_info=self.metadata, id_=self.doc_id)
        except ImportError:
            return self.to_dict()


class SchemaKnowledgeBuilder:
    """Builds structured, retrieval-optimized text representations of database schemas."""

    @classmethod
    def build_table_document(
        cls,
        table: SchemaTable,
        relationships: list[SchemaRelationship] | None = None,
        redact_sensitive: bool = False
    ) -> SchemaKnowledgeDocument:
        """Creates a dedicated knowledge document for a single table/entity."""
        lines = []
        lines.append(f"# HR DATABASE TABLE: {table.table_name.upper()}")
        lines.append(f"Business Name: {table.business_name or table.table_name}")
        lines.append(f"HR Business Entity: {table.business_entity}")
        lines.append(f"Table Type: {table.table_type}")
        lines.append(f"Importance Level: {table.importance_level} (Score: {table.importance_score}/100)")
        lines.append(f"Description: {table.description or 'No description provided.'}")
        if table.uses_effective_dating:
            lines.append("Effective Dating: YES (Table contains temporal effective date tracking)")

        lines.append("\n## COLUMNS & ATTRIBUTES:")
        col_meta_list = []
        has_sensitive_fields = False

        for col in table.columns:
            if redact_sensitive and col.is_sensitive:
                has_sensitive_fields = True
                lines.append(f"- {col.column_name}: [REDACTED SENSITIVE FIELD - {col.sensitive_category}]")
                continue

            pk_tag = " [PRIMARY KEY]" if col.is_primary_key else ""
            fk_tag = " [FOREIGN KEY]" if col.is_foreign_key else ""
            metric_tag = f" [METRIC: {col.default_aggregation}]" if col.is_metric else ""
            dim_tag = " [DIMENSION]" if col.is_dimension else ""
            date_tag = f" [DATE_ROLE: {col.date_role}]" if col.is_date_field else ""
            sens_tag = f" [SENSITIVE: {col.sensitive_category}]" if col.is_sensitive else ""
            if col.is_sensitive:
                has_sensitive_fields = True

            desc = col.business_definition or col.description or ""
            concept = f" (HR Concept: {col.hr_concept})" if col.hr_concept else ""

            lines.append(
                f"- `{col.column_name}` ({col.normalized_data_type}){pk_tag}{fk_tag}{metric_tag}{dim_tag}{date_tag}{sens_tag}{concept}: {desc}"
            )
            col_meta_list.append(col.column_name)

        # Relationships
        if relationships:
            relevant_rels = [
                r for r in relationships
                if r.source_table_name.lower() == table.table_name.lower() or r.target_table_name.lower() == table.table_name.lower()
            ]
            if relevant_rels:
                lines.append("\n## JOIN RELATIONSHIPS:")
                for r in relevant_rels:
                    lines.append(
                        f"- {r.source_table_name}.{r.source_column_name} -> {r.target_table_name}.{r.target_column_name} "
                        f"({r.relationship_type}, Source: {r.relationship_source}, Confidence: {r.confidence})"
                    )

        content = "\n".join(lines)
        doc_id = f"schema_tbl_{table.database_id}_{table.table_name}"

        metadata = {
            "doc_type": "schema_table",
            "database_id": table.database_id,
            "table_name": table.table_name,
            "business_name": table.business_name,
            "business_entity": table.business_entity,
            "importance_level": table.importance_level,
            "importance_score": table.importance_score,
            "has_sensitive_fields": has_sensitive_fields,
            "uses_effective_dating": table.uses_effective_dating,
            "status": table.status,
            "column_count": len(table.columns)
        }

        return SchemaKnowledgeDocument(
            doc_id=doc_id,
            text_content=content,
            metadata=metadata,
            doc_type="schema_table",
            database_id=table.database_id,
            table_name=table.table_name,
            business_entity=table.business_entity
        )

    @classmethod
    def build_schema_catalog_document(
        cls,
        database_id: str,
        tables: list[SchemaTable],
        relationships: list[SchemaRelationship],
        redact_sensitive: bool = False
    ) -> SchemaKnowledgeDocument:
        """Creates a holistic database schema overview document summarizing all entities and join paths."""
        lines = []
        lines.append(f"# DATABASE SCHEMA OVERVIEW: {database_id.upper()}")
        lines.append(f"Total Tables & Views: {len(tables)}")
        lines.append(f"Total Discovered Relationships: {len(relationships)}")
        lines.append("\n## BUSINESS ENTITIES:")

        for t in tables:
            key_cols = [c.column_name for c in t.columns if c.is_primary_key or c.is_foreign_key or c.is_metric][:5]
            lines.append(
                f"- **{t.table_name}** ({t.business_name or t.table_name}) [{t.business_entity}] "
                f"— Importance: {t.importance_level}. Key attributes: {', '.join(key_cols)}"
            )

        lines.append("\n## CANONICAL JOIN GRAPH:")
        for r in relationships:
            lines.append(
                f"- `{r.source_table_name}.{r.source_column_name}` JOIN `{r.target_table_name}.{r.target_column_name}` "
                f"[{r.relationship_source} | {r.confidence} confidence]"
            )

        content = "\n".join(lines)
        doc_id = f"schema_catalog_{database_id}"

        metadata = {
            "doc_type": "schema_catalog",
            "database_id": database_id,
            "table_count": len(tables),
            "relationship_count": len(relationships),
            "redacted_sensitive": redact_sensitive
        }

        return SchemaKnowledgeDocument(
            doc_id=doc_id,
            text_content=content,
            metadata=metadata,
            doc_type="schema_catalog",
            database_id=database_id
        )

    @classmethod
    def build_all_documents(
        cls,
        db: Session,
        database_id: str,
        redact_sensitive: bool = False
    ) -> list[SchemaKnowledgeDocument]:
        """Builds all LlamaIndex-compatible documents for a database schema."""
        tables = db.query(SchemaTable).filter_by(database_id=database_id).all()
        relationships = db.query(SchemaRelationship).filter_by(database_id=database_id).all()

        docs: list[SchemaKnowledgeDocument] = []

        # 1. Global catalog document
        catalog_doc = cls.build_schema_catalog_document(
            database_id=database_id,
            tables=tables,
            relationships=relationships,
            redact_sensitive=redact_sensitive
        )
        docs.append(catalog_doc)

        # 2. Per-table documents
        for t in tables:
            tbl_doc = cls.build_table_document(
                table=t,
                relationships=relationships,
                redact_sensitive=redact_sensitive
            )
            docs.append(tbl_doc)

        return docs
