"""Deterministic HR KPI Calculation Engine."""

import datetime
from typing import Dict, Any, Optional
import pandas as pd
from .schemas import KPISummary


class KPIEngine:
    """Computes standard deterministic HR KPIs on authorized datasets."""

    @classmethod
    def calculate_kpis(cls, df: pd.DataFrame) -> KPISummary:
        total_records = len(df)
        if total_records == 0:
            return KPISummary(total_records=0)

        lower_cols = {col.lower(): col for col in df.columns}

        # 1. Headcount & Status
        active_cnt = None
        term_cnt = None
        attrition_rate = None
        retention_rate = None

        if "status" in lower_cols:
            status_col = lower_cols["status"]
            active_cnt = int((df[status_col].astype(str).str.lower() == "active").sum())
            term_cnt = int((df[status_col].astype(str).str.lower() == "terminated").sum())
            if total_records > 0:
                attrition_rate = round((term_cnt / total_records) * 100, 2)
                retention_rate = round((active_cnt / total_records) * 100, 2)

        # 2. Compensation & Payroll
        salary_col = None
        for cand in ["base_salary", "salary", "compensation", "budget"]:
            if cand in lower_cols:
                salary_col = lower_cols[cand]
                break

        avg_comp = None
        med_comp = None
        tot_payroll = None

        if salary_col and pd.api.types.is_numeric_dtype(df[salary_col]):
            clean_sal = df[salary_col].dropna()
            if not clean_sal.empty:
                avg_comp = round(float(clean_sal.mean()), 2)
                med_comp = round(float(clean_sal.median()), 2)
                tot_payroll = round(float(clean_sal.sum()), 2)

        # 3. Tenure
        avg_tenure = None
        hire_col = lower_cols.get("hire_date")
        if hire_col:
            try:
                hire_series = pd.to_datetime(df[hire_col], errors="coerce")
                now_dt = pd.Timestamp.now()
                valid_hires = hire_series.dropna()
                if not valid_hires.empty:
                    tenures = (now_dt - valid_hires).dt.days / 365.25
                    avg_tenure = round(float(tenures.mean()), 2)
            except Exception:
                pass

        # 4. Gender Representation
        gender_dist = {}
        gender_col = lower_cols.get("gender")
        if gender_col:
            counts = df[gender_col].value_counts(dropna=True)
            total_g = counts.sum()
            for g_val, cnt in counts.items():
                gender_dist[str(g_val)] = round((cnt / max(total_g, 1)) * 100, 1)

        # 5. Additional custom metrics
        custom = {}
        compa_col = lower_cols.get("compa_ratio")
        if compa_col and pd.api.types.is_numeric_dtype(df[compa_col]):
            custom["avg_compa_ratio"] = round(float(df[compa_col].dropna().mean()), 2)

        perf_col = lower_cols.get("rating") or lower_cols.get("performance_rating")
        if perf_col and pd.api.types.is_numeric_dtype(df[perf_col]):
            custom["avg_performance_rating"] = round(float(df[perf_col].dropna().mean()), 2)

        return KPISummary(
            total_records=total_records,
            active_headcount=active_cnt,
            terminated_headcount=term_cnt,
            attrition_rate_pct=attrition_rate,
            retention_rate_pct=retention_rate,
            avg_compensation=avg_comp,
            median_compensation=med_comp,
            total_payroll=tot_payroll,
            avg_tenure_years=avg_tenure,
            gender_distribution=gender_dist,
            custom_kpis=custom
        )
