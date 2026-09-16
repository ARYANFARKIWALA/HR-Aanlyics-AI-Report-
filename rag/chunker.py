"""Module 5: Semantic Chunker.

Segments knowledge documents into coherent semantic chunks:
- REPORT_OVERVIEW
- TABLE_RELATIONSHIPS
- BUSINESS_RULE
- EFFECTIVE_DATING
- SECURITY_LOGIC
- ORIGINAL_SQL
- SCHEMA_DEFINITION

Preserves complete metadata on every generated chunk.
"""

from typing import Dict, Any, List, Optional


class SemanticChunk:
    """Represents an individual chunk of knowledge with preserved metadata."""

    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        chunk_text: str,
        chunk_type: str,
        database_id: str,
        source_type: str,
        source_id: Optional[str] = None,
        report_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        table_names: Optional[List[str]] = None,
        column_names: Optional[List[str]] = None,
        version: int = 1,
        is_active: bool = True,
        security_level: str = "STANDARD"
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.chunk_text = chunk_text
        self.chunk_type = chunk_type
        self.database_id = database_id
        self.source_type = source_type
        self.source_id = source_id
        self.report_id = report_id
        self.rule_id = rule_id
        self.table_names = table_names or []
        self.column_names = column_names or []
        self.version = version
        self.is_active = is_active
        self.security_level = security_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_text": self.chunk_text,
            "chunk_type": self.chunk_type,
            "database_id": self.database_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "report_id": self.report_id,
            "rule_id": self.rule_id,
            "table_names": self.table_names,
            "column_names": self.column_names,
            "version": self.version,
            "is_active": self.is_active,
            "security_level": self.security_level,
        }


class SemanticChunker:
    """Chunks documents into semantic units based on domain sections."""

    @classmethod
    def chunk_sql_report(
        cls,
        doc_id: str,
        report_data: Dict[str, Any],
        database_id: str
    ) -> List[SemanticChunk]:
        """Creates semantic chunks for an approved Module 2 SQL report."""
        chunks = []
        r_id = report_data.get("id")
        code = report_data.get("report_code") or f"RPT-{r_id}"
        name = report_data.get("report_name", "")
        tables = report_data.get("tables", [])
        columns = report_data.get("columns", [])
        joins = report_data.get("joins", [])
        filters = report_data.get("filters", [])
        sql_query = report_data.get("sql_query", "")
        desc = report_data.get("description", "")
        purpose = report_data.get("business_purpose", "")

        # 1. Report Overview Chunk
        overview_text = (
            f"REPORT: {name} ({code})\n"
            f"Category: {report_data.get('category', 'General')}\n"
            f"Description: {desc}\n"
            f"Business Purpose: {purpose}"
        )
        chunks.append(SemanticChunk(
            chunk_id=f"{doc_id}_overview",
            document_id=doc_id,
            chunk_text=overview_text,
            chunk_type="REPORT_OVERVIEW",
            database_id=database_id,
            source_type="SQL_REPORT",
            source_id=code,
            report_id=r_id,
            table_names=tables,
            column_names=columns
        ))

        # 2. Tables & Relationships Chunk
        if tables or joins:
            joins_text = "\n".join([f"- {j}" for j in joins]) if joins else "No explicit joins."
            rel_text = (
                f"REPORT SCHEMA RELATIONSHIPS: {name}\n"
                f"Tables Used: {', '.join(tables)}\n"
                f"Columns Selected: {', '.join(columns[:20])}\n"
                f"Join Paths:\n{joins_text}"
            )
            chunks.append(SemanticChunk(
                chunk_id=f"{doc_id}_relationships",
                document_id=doc_id,
                chunk_text=rel_text,
                chunk_type="TABLE_RELATIONSHIPS",
                database_id=database_id,
                source_type="SQL_REPORT",
                source_id=code,
                report_id=r_id,
                table_names=tables,
                column_names=columns
            ))

        # 3. Effective Dating Chunk (if applicable)
        if report_data.get("uses_effective_dating"):
            eff_text = (
                f"EFFECTIVE DATING LOGIC: {name}\n"
                f"This report applies temporal effective date tracking for employee records.\n"
                f"Filter expression: CURRENT_DATE BETWEEN effective_start_date AND effective_end_date"
            )
            chunks.append(SemanticChunk(
                chunk_id=f"{doc_id}_effective_dating",
                document_id=doc_id,
                chunk_text=eff_text,
                chunk_type="EFFECTIVE_DATING",
                database_id=database_id,
                source_type="SQL_REPORT",
                source_id=code,
                report_id=r_id,
                table_names=tables
            ))

        # 4. Security Logic Chunk (if applicable)
        if report_data.get("uses_security_filter"):
            sec_text = (
                f"SECURITY FILTER LOGIC: {name}\n"
                f"This report contains access restrictions scoped to organization or department level."
            )
            chunks.append(SemanticChunk(
                chunk_id=f"{doc_id}_security",
                document_id=doc_id,
                chunk_text=sec_text,
                chunk_type="SECURITY_LOGIC",
                database_id=database_id,
                source_type="SQL_REPORT",
                source_id=code,
                report_id=r_id,
                table_names=tables,
                security_level="CRITICAL"
            ))

        # 5. Original SQL Chunk
        if sql_query:
            sql_text = (
                f"ORIGINAL VERIFIED SQL: {name}\n"
                f"Database: {database_id}\n"
                f"```sql\n{sql_query}\n```"
            )
            chunks.append(SemanticChunk(
                chunk_id=f"{doc_id}_sql",
                document_id=doc_id,
                chunk_text=sql_text,
                chunk_type="ORIGINAL_SQL",
                database_id=database_id,
                source_type="SQL_REPORT",
                source_id=code,
                report_id=r_id,
                table_names=tables,
                column_names=columns
            ))

        return chunks

    @classmethod
    def chunk_business_rule(
        cls,
        doc_id: str,
        rule_data: Dict[str, Any],
        database_id: str
    ) -> List[SemanticChunk]:
        """Creates semantic chunk for an approved Module 4 business rule."""
        code = rule_data.get("rule_code", "")
        name = rule_data.get("rule_name", "")
        rtype = rule_data.get("rule_type", "FILTER")
        expr = rule_data.get("rule_expression", "")
        nl = rule_data.get("natural_language_rule", "")
        priority = rule_data.get("priority", "MEDIUM")
        mandatory = rule_data.get("mandatory", False)
        tbl = rule_data.get("table_name")
        col = rule_data.get("column_name")

        chunk_type = "SECURITY_LOGIC" if rtype in ["SECURITY", "DATA_ACCESS"] else (
            "EFFECTIVE_DATING" if rtype == "EFFECTIVE_DATING" else "BUSINESS_RULE"
        )
        sec_level = "CRITICAL" if rtype in ["SECURITY", "DATA_ACCESS"] or priority == "CRITICAL" else "STANDARD"

        rule_text = (
            f"BUSINESS RULE: {name} ({code})\n"
            f"Category: {rtype} | Priority: {priority} | Mandatory: {'YES' if mandatory else 'NO'}\n"
            f"Target Entity: {tbl or 'General'}.{col or '*'}\n"
            f"Natural Language Meaning: {nl}\n"
            f"Filter Expression: {expr}"
        )

        return [
            SemanticChunk(
                chunk_id=f"{doc_id}_rule",
                document_id=doc_id,
                chunk_text=rule_text,
                chunk_type=chunk_type,
                database_id=database_id,
                source_type="BUSINESS_RULE",
                source_id=code,
                rule_id=rule_data.get("id"),
                table_names=[tbl] if tbl else [],
                column_names=[col] if col else [],
                security_level=sec_level
            )
        ]

    @classmethod
    def chunk_schema_table(
        cls,
        doc_id: str,
        table_data: Dict[str, Any],
        database_id: str
    ) -> List[SemanticChunk]:
        """Creates semantic chunks for an enriched Module 3 schema table."""
        tbl_name = table_data.get("table_name", "")
        b_name = table_data.get("business_name") or tbl_name
        entity = table_data.get("business_entity", "OTHER")
        desc = table_data.get("description", "")
        cols = table_data.get("columns", [])
        rels = table_data.get("relationships", [])

        chunks = []

        # 1. Schema Definition Chunk
        col_summary = [f"{c.get('name') or c.get('column_name')} ({c.get('normalized_data_type', 'STRING')})" for c in cols[:15]]
        schema_text = (
            f"DATABASE TABLE: {tbl_name} ({b_name})\n"
            f"Entity Type: {entity}\n"
            f"Description: {desc}\n"
            f"Key Columns: {', '.join(col_summary)}"
        )
        chunks.append(SemanticChunk(
            chunk_id=f"{doc_id}_def",
            document_id=doc_id,
            chunk_text=schema_text,
            chunk_type="SCHEMA_DEFINITION",
            database_id=database_id,
            source_type="TABLE_METADATA",
            source_id=tbl_name,
            table_names=[tbl_name],
            column_names=[c.get("name") or c.get("column_name") for c in cols]
        ))

        # 2. Join Relationships Chunk
        if rels:
            join_lines = []
            for r in rels:
                src_t = r.get("source_table", "")
                tgt_t = r.get("target_table", "")
                src_c = r.get("source_column", "")
                tgt_c = r.get("target_column", "")
                join_lines.append(f"- {src_t}.{src_c} = {tgt_t}.{tgt_c} ({r.get('relationship_type', 'MANY_TO_ONE')})")

            rel_text = (
                f"CANONICAL JOIN PATHS FOR TABLE: {tbl_name}\n"
                f"{chr(10).join(join_lines)}"
            )
            chunks.append(SemanticChunk(
                chunk_id=f"{doc_id}_joins",
                document_id=doc_id,
                chunk_text=rel_text,
                chunk_type="TABLE_RELATIONSHIPS",
                database_id=database_id,
                source_type="TABLE_METADATA",
                source_id=tbl_name,
                table_names=[tbl_name] + [r.get("target_table", "") for r in rels]
            ))

        return chunks

    @classmethod
    def chunk_glossary_term(
        cls,
        doc_id: str,
        term_data: Dict[str, Any],
        database_id: str
    ) -> List[SemanticChunk]:
        """Creates semantic chunks for an HR business glossary term or metric definition."""
        term = term_data.get("term", "")
        definition = term_data.get("definition", "")
        formula = term_data.get("formula", "")
        category = term_data.get("category", "HR_TERMINOLOGY")
        tbls = term_data.get("table_names", [])
        cols = term_data.get("column_names", [])

        term_text = (
            f"HR BUSINESS GLOSSARY: {term}\n"
            f"Category: {category}\n"
            f"Definition: {definition}\n"
            f"Calculation / Reference: {formula or 'Standard operational term'}\n"
            f"Applicable Tables: {', '.join(tbls) if tbls else 'General'}"
        )
        return [
            SemanticChunk(
                chunk_id=f"{doc_id}_glossary",
                document_id=doc_id,
                chunk_text=term_text,
                chunk_type="GLOSSARY_DEFINITION",
                database_id=database_id,
                source_type="HR_GLOSSARY",
                source_id=term,
                table_names=tbls,
                column_names=cols
            )
        ]

    @classmethod
    def chunk_report_definition(
        cls,
        doc_id: str,
        def_data: Dict[str, Any],
        database_id: str
    ) -> List[SemanticChunk]:
        """Creates semantic chunks for an approved report definition or KPI specification."""
        name = def_data.get("name", "")
        desc = def_data.get("description", "")
        metrics = def_data.get("metrics", [])
        dims = def_data.get("dimensions", [])
        tbls = def_data.get("table_names", [])

        def_text = (
            f"APPROVED REPORT DEFINITION: {name}\n"
            f"Description: {desc}\n"
            f"Target Metrics: {', '.join(metrics) if metrics else 'Standard metrics'}\n"
            f"Dimensions: {', '.join(dims) if dims else 'Organizational dimensions'}\n"
            f"Applicable Tables: {', '.join(tbls) if tbls else 'General'}"
        )
        return [
            SemanticChunk(
                chunk_id=f"{doc_id}_report_def",
                document_id=doc_id,
                chunk_text=def_text,
                chunk_type="REPORT_DEFINITION",
                database_id=database_id,
                source_type="REPORT_DEFINITION",
                source_id=name,
                table_names=tbls
            )
        ]

