"""Document ingestion for HR policies and SQL repository knowledge."""

from typing import Any, ClassVar

from sqlalchemy.orm import Session

from backend.database.models import SQLRepository


class PolicyDocument:
    def __init__(self, doc_id: str, title: str, category: str, content: str):
        self.doc_id = doc_id
        self.title = title
        self.category = category
        self.content = content

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "category": self.category,
            "content": self.content
        }


class DocumentIngester:
    """Ingests enterprise HR policies and catalogs SQL repository knowledge."""

    SAMPLE_POLICIES: ClassVar[list[PolicyDocument]] = [
        PolicyDocument(
            doc_id="POL-001",
            title="Remote and Hybrid Workplace Policy",
            category="Workplace",
            content="""Employees in eligible job profiles (Engineering, Product, Marketing) may work under Hybrid (2-3 days in office) or Fully Remote arrangements upon manager approval. Remote employees are provided a $1,000 one-time home office setup stipend and a $75/month high-speed internet reimbursement. Performance expectations remain identical regardless of physical work location."""
        ),
        PolicyDocument(
            doc_id="POL-002",
            title="Annual Merit Increase & Compa-Ratio Matrix Guidelines",
            category="Compensation",
            content="""Annual merit increases are calibrated based on employee performance ratings and current compa-ratio:
- Rating 5 (Outstanding) with Compa-Ratio < 0.95: 8% to 12% increase.
- Rating 4 (Exceeds) with Compa-Ratio 0.95-1.05: 5% to 7% increase.
- Rating 3 (Meets) with Compa-Ratio 1.00-1.10: 3% to 4% increase.
Employees with compa-ratio above 1.20 receive lump-sum performance bonuses rather than base salary adjustments to maintain salary grade equity."""
        ),
        PolicyDocument(
            doc_id="POL-003",
            title="Voluntary Resignation, Offboarding & Severance Policy",
            category="Offboarding",
            content="""Exiting employees must provide at least two weeks written notice. Accrued but unused annual leave days are paid out in the final paycheck subject to local state regulations. Involuntary terminations resulting from organizational restructuring qualify for 2 weeks of base pay per year of service, plus subsidized COBRA health benefits for 3 months."""
        ),
        PolicyDocument(
            doc_id="POL-004",
            title="Parental Leave and Family Care Policy",
            category="Benefits",
            content="""All full-time employees with at least 6 months of continuous service are eligible for 16 weeks of 100% paid parental leave for the birth, adoption, or foster placement of a child. Parental leave can be taken consecutively or in blocks within the first 12 months following the qualifying event."""
        ),
        PolicyDocument(
            doc_id="POL-005",
            title="Performance Improvement Plan (PIP) & Review Cycles",
            category="Performance",
            content="""Performance reviews are conducted annually in Q4 with a mid-year check-in in Q2. Ratings range from 1 (Unsatisfactory) to 5 (Outstanding). A rating of 2 triggers a mandatory 60-day Performance Improvement Plan (PIP) with clearly defined milestones."""
        ),
    ]

    @classmethod
    def get_all_policies(cls) -> list[PolicyDocument]:
        return cls.SAMPLE_POLICIES

    @classmethod
    def get_sql_repository_documents(cls, session: Session) -> list[dict[str, Any]]:
        """Retrieves and packages all enterprise SQL templates for vector indexing."""
        records = session.query(SQLRepository).all()
        docs = []
        for r in records:
            composite_text = f"Title: {r.report_title}\nCategory: {r.category}\nDescription: {r.business_description}\nBusiness Rules: {r.business_rules_explained}\nEffective Dating: {r.effective_dating_explained}\nTags: {r.tags}\nSQL: {r.raw_sql}"
            docs.append({
                "id": r.id,
                "title": r.report_title,
                "category": r.category,
                "description": r.business_description,
                "raw_sql": r.raw_sql,
                "business_rules": r.business_rules_explained,
                "joins_explained": r.joins_explained,
                "effective_dating_explained": r.effective_dating_explained,
                "tags": r.tags,
                "composite_text": composite_text
            })
        return docs
