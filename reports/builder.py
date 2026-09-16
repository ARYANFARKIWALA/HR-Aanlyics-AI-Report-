"""Enterprise HR Report Builder.

Assembles comprehensive report structures combining:
- Executive metadata & classifications
- KPI summary cards
- AI executive strategic narrative
- Structured tabular SQL data
- Query lineage, business rules, and effective-dating notes
"""

import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from analytics.metrics import HRMetricsCalculator
from ai.model import llm_client
from ai.prompts.report_prompts import REPORT_NARRATIVE_PROMPT


class ReportData:
    """Encapsulates all components required for enterprise PDF / Excel report rendering."""

    def __init__(
        self,
        report_id: str,
        title: str,
        category: str,
        requested_by: str,
        generated_at: str,
        kpis: Dict[str, Any],
        executive_summary: str,
        data_columns: List[str],
        data_rows: List[Dict[str, Any]],
        sql_query: str,
        business_rules: str,
        effective_dating_notes: str
    ):
        self.report_id = report_id
        self.title = title
        self.category = category
        self.requested_by = requested_by
        self.generated_at = generated_at
        self.kpis = kpis
        self.executive_summary = executive_summary
        self.data_columns = data_columns
        self.data_rows = data_rows
        self.sql_query = sql_query
        self.business_rules = business_rules
        self.effective_dating_notes = effective_dating_notes

    def to_dataframe(self) -> pd.DataFrame:
        if not self.data_rows:
            return pd.DataFrame(columns=self.data_columns)
        return pd.DataFrame(self.data_rows)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "title": self.title,
            "category": self.category,
            "requested_by": self.requested_by,
            "generated_at": self.generated_at,
            "kpis": self.kpis,
            "executive_summary": self.executive_summary,
            "data_columns": self.data_columns,
            "row_count": len(self.data_rows),
            "sql_query": self.sql_query,
            "business_rules": self.business_rules,
            "effective_dating_notes": self.effective_dating_notes
        }


class ReportBuilder:
    """Coordinates data gathering, metrics calculation, and narrative synthesis."""

    @classmethod
    def assemble_report(
        cls,
        session: Session,
        title: str,
        category: str,
        sql_query: str,
        data_columns: List[str],
        data_rows: List[Dict[str, Any]],
        requested_by: str = "HR Leadership",
        business_rules: str = "Standard enterprise payroll and effective-dating rules applied.",
        effective_dating_notes: str = "Records evaluated as of current active snapshot."
    ) -> ReportData:
        report_id = f"REP-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        generated_at = datetime.datetime.utcnow().strftime("%B %d, %Y - %H:%M UTC")

        # 1. Fetch organizational KPIs
        kpis = HRMetricsCalculator.get_executive_summary_kpis(session)

        # 2. Synthesize AI Executive Narrative
        preview_data = data_rows[:10] if data_rows else []
        prompt = f"""Generate an executive briefing for report: '{title}'.
Report Category: {category}
Current Organization Snapshot:
- Active Headcount: {kpis['active_headcount']}
- Attrition Rate: {kpis['attrition_rate_pct']}% (Voluntary: {kpis['voluntary_attrition_rate_pct']}%)
- Average Base Salary: ${kpis['avg_base_salary']:,.2f}
- Average Compa-Ratio: {kpis['avg_compa_ratio']}
- Female Representation: {kpis['female_representation_pct']}%

Sample Tabular Query Data:
{preview_data}

Business Rules Applied:
{business_rules}
"""
        executive_summary = llm_client.generate(prompt, system_instruction=REPORT_NARRATIVE_PROMPT)

        return ReportData(
            report_id=report_id,
            title=title,
            category=category,
            requested_by=requested_by,
            generated_at=generated_at,
            kpis=kpis,
            executive_summary=executive_summary,
            data_columns=data_columns,
            data_rows=data_rows,
            sql_query=sql_query,
            business_rules=business_rules,
            effective_dating_notes=effective_dating_notes
        )
