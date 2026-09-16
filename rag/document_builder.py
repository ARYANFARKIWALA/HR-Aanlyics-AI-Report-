"""Module 5: Knowledge Document Builder.

Translates:
- Module 1/3 Schema Metadata
- Module 2 Approved SQL Reports
- Module 4 Approved & Active Business Rules
into standardized RAG documents ready for chunking and vector storage.

STRICT INVARIANT: Under no circumstances does this builder index unapproved,
draft, inactive, or rejected rules. Only ACTIVE and current rules are indexed.
"""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models_repo import SQLReport
from backend.database.models_rules import BusinessRule
from backend.database.models_schema import SchemaRelationship, SchemaTable

from .chunker import SemanticChunk, SemanticChunker

logger = logging.getLogger("rag.document_builder")


class DocumentBuilder:
    """Constructs knowledge documents and chunks from organizational knowledge sources."""

    def __init__(self, db: Session):
        self.db = db

    def build_all_for_database(self, database_id: str) -> list[tuple[dict[str, Any], list[SemanticChunk]]]:
        """Gathers schema, reports, and approved rules for a target database."""
        results = []

        # 1. Process Schema Tables (M1 & M3)
        tables = self.db.query(SchemaTable).filter_by(database_id=database_id).all()
        for tbl in tables:
            doc_data, chunks = self.build_schema_table_document(tbl)
            results.append((doc_data, chunks))

        # 2. Process Approved SQL Reports (M2)
        reports = (
            self.db.query(SQLReport)
            .filter(
                SQLReport.database_id == database_id,
                SQLReport.status.in_(["APPROVED", "VALID"])
            )
            .all()
        )
        for rpt in reports:
            doc_data, chunks = self.build_sql_report_document(rpt)
            results.append((doc_data, chunks))

        # 3. Process Approved Business Rules (M4) - Strictly ACTIVE & current
        rules = (
            self.db.query(BusinessRule)
            .filter(
                BusinessRule.database_id == database_id,
                BusinessRule.status == "ACTIVE",
                BusinessRule.is_current == True
            )
            .all()
        )
        for r in rules:
            doc_data, chunks = self.build_business_rule_document(r)
            results.append((doc_data, chunks))

        # 4. Process Canonical HR Business Glossary Terms
        for g_term in self.get_canonical_glossary_terms():
            doc_data, chunks = self.build_glossary_term_document(g_term, database_id)
            results.append((doc_data, chunks))

        # 5. Process Approved Report Definitions
        for r_def in self.get_canonical_report_definitions():
            doc_data, chunks = self.build_report_definition_document(r_def, database_id)
            results.append((doc_data, chunks))

        return results


    def build_schema_table_document(self, tbl: SchemaTable) -> tuple[dict[str, Any], list[SemanticChunk]]:
        """Transforms a SchemaTable into document and semantic chunks."""
        doc_id = f"DOC_TBL_{tbl.database_id}_{tbl.table_name}"
        cols = [{"name": c.column_name, "normalized_data_type": c.normalized_data_type} for c in tbl.columns]

        # Gather relationships
        out_rels = (
            self.db.query(SchemaRelationship)
            .filter_by(source_table_id=tbl.id)
            .all()
        )
        rels = [
            {
                "source_table": r.source_table_name,
                "source_column": r.source_column_name,
                "target_table": r.target_table_name,
                "target_column": r.target_column_name,
                "relationship_type": r.relationship_type
            }
            for r in out_rels
        ]

        table_data = {
            "table_name": tbl.table_name,
            "business_name": tbl.business_name,
            "business_entity": tbl.business_entity,
            "description": tbl.description,
            "columns": cols,
            "relationships": rels
        }

        chunks = SemanticChunker.chunk_schema_table(doc_id, table_data, tbl.database_id)

        doc_data = {
            "document_id": doc_id,
            "source_type": "TABLE_METADATA",
            "source_id": tbl.table_name,
            "title": f"Table: {tbl.table_name} ({tbl.business_name or tbl.table_name})",
            "content": tbl.description or f"Table metadata for {tbl.table_name}",
            "database_id": tbl.database_id,
            "version": 1,
            "is_active": True
        }
        return doc_data, chunks

    def build_sql_report_document(self, rpt: SQLReport) -> tuple[dict[str, Any], list[SemanticChunk]]:
        """Transforms an approved SQLReport into document and semantic chunks."""
        doc_id = f"DOC_RPT_{rpt.database_id}_{rpt.id}"
        meta = rpt.metadata_rel

        tables_list = []
        columns_list = []
        joins_list = []

        if meta:
            if meta.tables_json:
                try:
                    tables_list = json.loads(meta.tables_json) if isinstance(meta.tables_json, str) else list(meta.tables_json)
                except Exception:
                    tables_list = []
            if meta.columns_json:
                try:
                    columns_list = json.loads(meta.columns_json) if isinstance(meta.columns_json, str) else list(meta.columns_json)
                except Exception:
                    columns_list = []
            if meta.joins_json:
                try:
                    joins_list = json.loads(meta.joins_json) if isinstance(meta.joins_json, str) else list(meta.joins_json)
                except Exception:
                    joins_list = []

        report_data = {
            "id": rpt.id,
            "report_code": rpt.report_code,
            "report_name": rpt.report_name,
            "category": rpt.category,
            "description": rpt.description,
            "business_purpose": rpt.business_purpose,
            "sql_query": rpt.sql_query,
            "uses_effective_dating": meta.uses_effective_dating if meta else False,
            "uses_security_filter": meta.uses_security_filter if meta else False,
            "tables": tables_list,
            "columns": columns_list,
            "joins": joins_list,
        }


        chunks = SemanticChunker.chunk_sql_report(doc_id, report_data, rpt.database_id)

        doc_data = {
            "document_id": doc_id,
            "source_type": "SQL_REPORT",
            "source_id": rpt.report_code,
            "title": f"Report: {rpt.report_name} ({rpt.report_code})",
            "content": f"{rpt.description}\n{rpt.business_purpose or ''}",
            "database_id": rpt.database_id,
            "report_id": rpt.id,
            "version": rpt.version,
            "is_active": True
        }
        return doc_data, chunks

    def build_business_rule_document(self, rule: BusinessRule) -> tuple[dict[str, Any], list[SemanticChunk]]:
        """Transforms an approved BusinessRule into document and semantic chunks."""
        if rule.status != "ACTIVE" or not rule.is_current:
            raise ValueError(f"Cannot index rule '{rule.rule_code}' with status '{rule.status}'. Only ACTIVE rules allowed.")

        doc_id = f"DOC_RULE_{rule.database_id}_{rule.id}"
        rule_data = {
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "rule_type": rule.rule_type,
            "rule_expression": rule.rule_expression,
            "natural_language_rule": rule.natural_language_rule,
            "priority": rule.priority,
            "mandatory": rule.mandatory,
            "table_name": rule.table_name,
            "column_name": rule.column_name
        }

        chunks = SemanticChunker.chunk_business_rule(doc_id, rule_data, rule.database_id)

        doc_data = {
            "document_id": doc_id,
            "source_type": "BUSINESS_RULE",
            "source_id": rule.rule_code,
            "title": f"Rule: {rule.rule_name} ({rule.rule_code})",
            "content": f"{rule.natural_language_rule}\nFilter: {rule.rule_expression}",
            "database_id": rule.database_id,
            "rule_id": rule.id,
            "version": rule.version,
            "is_active": True
        }
        return doc_data, chunks

    @classmethod
    def get_canonical_glossary_terms(cls) -> list[dict[str, Any]]:
        """Canonical HR definitions and metric formulas for organizational knowledge grounding."""
        return [
            {
                "term": "Active Employee",
                "category": "HR_TERMINOLOGY",
                "definition": "Active employee means an individual whose employee_status = 'ACTIVE' and who has not reached a formal termination date.",
                "formula": "employees.status = 'Active' AND employees.is_current = 1",
                "table_names": ["employees"],
                "column_names": ["status", "is_current"]
            },
            {
                "term": "Attrition",
                "category": "METRIC_DEFINITION",
                "definition": "Attrition represents the departure of employees from the organization through voluntary resignation or involuntary termination during a specified timeframe.",
                "formula": "COUNT(CASE WHEN status = 'Terminated' THEN 1 END) / COUNT(total_headcount)",
                "table_names": ["employees", "departments"],
                "column_names": ["status", "attrition_type", "termination_date"]
            },
            {
                "term": "Current Employee",
                "category": "HR_TERMINOLOGY",
                "definition": "Current employee refers strictly to the latest active point-in-time effective-dated record of the employee (is_current = 1).",
                "formula": "employees.is_current = 1 AND CURRENT_DATE BETWEEN effective_start_date AND effective_end_date",
                "table_names": ["employees"],
                "column_names": ["is_current", "effective_start_date", "effective_end_date"]
            },
            {
                "term": "Headcount",
                "category": "METRIC_DEFINITION",
                "definition": "Headcount is the total number of distinct active full-time and part-time workers employed in the business unit or organization at a designated snapshot point.",
                "formula": "COUNT(DISTINCT employees.id) WHERE status = 'Active' AND is_current = 1",
                "table_names": ["employees", "departments"],
                "column_names": ["id", "status", "is_current"]
            },
            {
                "term": "Compa-Ratio",
                "category": "CALCULATION_DEFINITION",
                "definition": "Compa-ratio measures an employee's actual base salary against the market midpoint for their assigned job grade: (Base Salary / Midpoint Salary).",
                "formula": "compensation_history.base_salary / job_profiles.mid_salary",
                "table_names": ["compensation_history", "job_profiles"],
                "column_names": ["base_salary", "mid_salary", "compa_ratio"]
            }
        ]

    @classmethod
    def get_canonical_report_definitions(cls) -> list[dict[str, Any]]:
        """Approved organizational report specifications and KPI templates."""
        return [
            {
                "name": "Departmental Headcount & Payroll Expenditure Report",
                "description": "Standard monthly headcount report tracking active workers, departmental budgets, and total payroll consumption.",
                "metrics": ["Headcount", "Total Payroll", "Budget Consumed %"],
                "dimensions": ["Department Name", "Cost Center"],
                "table_names": ["departments", "employees", "compensation_history"]
            },
            {
                "name": "Employee Attrition & Voluntary Turnover Report",
                "description": "Organizational turnover report tracking separations, voluntary resignations, and exit rates segmented by department.",
                "metrics": ["Voluntary Exits", "Involuntary Exits", "Turnover Rate %"],
                "dimensions": ["Department", "Work Location"],
                "table_names": ["employees", "departments"]
            },
            {
                "name": "Compensation Equity & Pay Grade Distribution",
                "description": "Salary equity analysis evaluating average base compensation and compa-ratios across salary grades and job families.",
                "metrics": ["Avg Base Salary", "Min Salary", "Max Salary", "Avg Compa-Ratio"],
                "dimensions": ["Job Family", "Salary Grade"],
                "table_names": ["job_profiles", "employees", "compensation_history"]
            }
        ]

    def build_glossary_term_document(
        self,
        term_data: dict[str, Any],
        database_id: str
    ) -> tuple[dict[str, Any], list[SemanticChunk]]:
        """Transforms an HR business glossary term into a RAG document and chunks."""
        clean_slug = term_data["term"].lower().replace(" ", "_").replace("-", "_")
        doc_id = f"DOC_GLOSS_{database_id}_{clean_slug}"
        chunks = SemanticChunker.chunk_glossary_term(doc_id, term_data, database_id)

        doc_data = {
            "document_id": doc_id,
            "source_type": "HR_GLOSSARY",
            "source_id": term_data["term"],
            "title": f"Glossary Term: {term_data['term']}",
            "content": f"{term_data['definition']}\nFormula/Reference: {term_data.get('formula', '')}",
            "database_id": database_id,
            "version": 1,
            "is_active": True
        }
        return doc_data, chunks

    def build_report_definition_document(
        self,
        def_data: dict[str, Any],
        database_id: str
    ) -> tuple[dict[str, Any], list[SemanticChunk]]:
        """Transforms an approved report definition into a RAG document and chunks."""
        clean_slug = def_data["name"].lower().replace(" ", "_").replace("&", "and")[:30]
        doc_id = f"DOC_RPTDEF_{database_id}_{clean_slug}"
        chunks = SemanticChunker.chunk_report_definition(doc_id, def_data, database_id)

        doc_data = {
            "document_id": doc_id,
            "source_type": "REPORT_DEFINITION",
            "source_id": def_data["name"],
            "title": f"Approved Report Definition: {def_data['name']}",
            "content": f"{def_data['description']}\nMetrics: {', '.join(def_data.get('metrics', []))}",
            "database_id": database_id,
            "version": 1,
            "is_active": True
        }
        return doc_data, chunks

