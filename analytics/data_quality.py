"""Data quality and integrity assessment engine."""


import pandas as pd

from .schemas import DataQualityReport


class DataQualityAuditor:
    """Evaluates data completeness, consistency, and structural anomalies."""

    @classmethod
    def audit(cls, df: pd.DataFrame) -> DataQualityReport:
        total_rows = len(df)
        if total_rows == 0:
            return DataQualityReport(
                quality_score=100.0,
                total_rows=0,
                completeness_pct=100.0,
                anomaly_count=0,
                issues=[]
            )

        issues: list[str] = []
        anomaly_count = 0

        # 1. Completeness
        total_cells = total_rows * len(df.columns)
        null_cells = int(df.isna().sum().sum())
        completeness = round(((total_cells - null_cells) / max(total_cells, 1)) * 100, 2)

        # 2. Check duplicate identifiers
        id_cols = [c for c in df.columns if str(c).lower() in ["id", "employee_id", "employee_number"]]
        for id_c in id_cols:
            dupes = df[id_c].duplicated().sum()
            if dupes > 0:
                issues.append(f"Found {dupes} duplicate identifier values in column '{id_c}'.")
                anomaly_count += int(dupes)

        # 3. Check negative values in currency/numeric metrics
        lower_map = {str(c).lower(): c for c in df.columns}
        for k in ["salary", "base_salary", "budget", "compa_ratio"]:
            if k in lower_map:
                col_name = lower_map[k]
                s = pd.to_numeric(df[col_name], errors="coerce").dropna()
                neg_cnt = (s < 0).sum()
                if neg_cnt > 0:
                    issues.append(f"Found {neg_cnt} invalid negative values in financial column '{col_name}'.")
                    anomaly_count += int(neg_cnt)

        # 4. Check chronological integrity (termination before hire)
        if "hire_date" in lower_map and "termination_date" in lower_map:
            h_col = lower_map["hire_date"]
            t_col = lower_map["termination_date"]
            h_dates = pd.to_datetime(df[h_col], errors="coerce")
            t_dates = pd.to_datetime(df[t_col], errors="coerce")
            invalids = ((t_dates < h_dates) & t_dates.notna() & h_dates.notna()).sum()
            if invalids > 0:
                issues.append(f"Found {invalids} records where termination_date precedes hire_date.")
                anomaly_count += int(invalids)

        # Compute composite quality score (0 - 100)
        score = completeness
        penalty = min(anomaly_count * 5.0, 30.0)
        final_score = max(0.0, round(score - penalty, 1))

        return DataQualityReport(
            quality_score=final_score,
            total_rows=total_rows,
            completeness_pct=completeness,
            anomaly_count=anomaly_count,
            issues=issues
        )
