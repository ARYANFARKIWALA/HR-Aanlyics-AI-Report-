"""HR Metrics and KPI Calculator Engine.

Computes core organizational human capital metrics:
- Active Headcount & Retention
- Annualized Voluntary vs Involuntary Attrition Rates
- Compa-Ratio & Compensation Equity
- Tenure Distributions
- EEO / Gender Diversity Metrics
"""

from typing import Dict, Any, List
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database.models import (
    Employee, Department, CompensationHistory,
    PerformanceReview, LeaveRecord, JobProfile
)


class HRMetricsCalculator:
    """Computes enterprise HR KPIs directly from the relational database."""

    @classmethod
    def get_executive_summary_kpis(cls, session: Session) -> Dict[str, Any]:
        """Returns top-level KPI snapshot for executive dashboards."""
        total_employees = session.query(Employee).count()
        active_headcount = session.query(Employee).filter(Employee.status == "Active", Employee.is_current == True).count()
        terminated_count = session.query(Employee).filter(Employee.status == "Terminated").count()
        voluntary_exits = session.query(Employee).filter(
            Employee.status == "Terminated", Employee.attrition_type == "Voluntary"
        ).count()
        involuntary_exits = session.query(Employee).filter(
            Employee.status == "Terminated", Employee.attrition_type == "Involuntary"
        ).count()

        # Attrition rate %
        attrition_rate = round((terminated_count / max(total_employees, 1)) * 100, 2)
        voluntary_attrition_rate = round((voluntary_exits / max(total_employees, 1)) * 100, 2)

        # Average Base Salary & Compa-Ratio
        comp_stats = session.query(
            func.avg(CompensationHistory.base_salary),
            func.avg(CompensationHistory.compa_ratio),
            func.sum(CompensationHistory.base_salary)
        ).join(Employee, Employee.id == CompensationHistory.employee_id)\
         .filter(Employee.status == "Active", Employee.is_current == True).first()

        avg_salary = round(comp_stats[0] or 0.0, 2)
        avg_compa_ratio = round(comp_stats[1] or 1.0, 2)
        total_payroll = round(comp_stats[2] or 0.0, 2)

        # Gender representation
        female_count = session.query(Employee).filter(
            Employee.gender == "Female", Employee.status == "Active", Employee.is_current == True
        ).count()
        female_rep_pct = round((female_count / max(active_headcount, 1)) * 100, 1)

        # Average performance score
        avg_perf = session.query(func.avg(PerformanceReview.rating)).first()[0]
        avg_perf_rating = round(avg_perf or 0.0, 2)

        # Department breakdown
        dept_counts = session.query(
            Department.name,
            func.count(Employee.id)
        ).join(Employee, Department.id == Employee.department_id)\
         .filter(Employee.status == "Active", Employee.is_current == True)\
         .group_by(Department.name).all()

        dept_summary = [{"department": d[0], "active_headcount": d[1]} for d in dept_counts]

        return {
            "total_headcount": total_employees,
            "active_headcount": active_headcount,
            "terminated_count": terminated_count,
            "voluntary_exits": voluntary_exits,
            "involuntary_exits": involuntary_exits,
            "attrition_rate_pct": attrition_rate,
            "voluntary_attrition_rate_pct": voluntary_attrition_rate,
            "avg_base_salary": avg_salary,
            "avg_compa_ratio": avg_compa_ratio,
            "total_payroll_annual": total_payroll,
            "female_representation_pct": female_rep_pct,
            "avg_performance_rating": avg_perf_rating,
            "department_breakdown": dept_summary,
            "calculated_at": datetime.datetime.utcnow().isoformat()
        }

    @classmethod
    def get_attrition_by_department(cls, session: Session) -> List[Dict[str, Any]]:
        """Calculates turnover breakdown across departments."""
        results = session.query(
            Department.name,
            func.count(func.nullif(Employee.status != "Active", True)),
            func.count(Employee.id)
        ).outerjoin(Employee, Department.id == Employee.department_id)\
         .group_by(Department.name).all()

        data = []
        for name, active, total in results:
            term = total - active
            pct = round((term / max(total, 1)) * 100, 2)
            data.append({
                "department": name,
                "active": active,
                "terminated": term,
                "total": total,
                "turnover_pct": pct
            })
        return sorted(data, key=lambda x: x["turnover_pct"], reverse=True)
