"""Interquartile Range (IQR) and Z-score outlier detection."""

from typing import List, Optional
import pandas as pd
import numpy as np
from .schemas import OutlierItem, ColumnClassification


class OutlierDetector:
    """Identifies statistical anomalies in HR compensation, tenure, and performance."""

    @classmethod
    def detect_outliers(
        cls,
        df: pd.DataFrame,
        classifications: List[ColumnClassification]
    ) -> List[OutlierItem]:
        outliers: List[OutlierItem] = []
        if len(df) < 4:
            return outliers

        id_col = None
        for c in df.columns:
            if str(c).lower() in ["employee_number", "employee_id", "id", "name"]:
                id_col = c
                break

        # Check all numeric & currency columns
        metric_cols = [c.column_name for c in classifications if c.semantic_type in ["CURRENCY", "NUMERIC"]]

        for col in metric_cols:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(series) < 4:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = round(q1 - 1.5 * iqr, 2)
            upper_bound = round(q3 + 1.5 * iqr, 2)
            extreme_lower = round(q1 - 3.0 * iqr, 2)
            extreme_upper = round(q3 + 3.0 * iqr, 2)

            for idx, val in series.items():
                if val < lower_bound or val > upper_bound:
                    is_extreme = val < extreme_lower or val > extreme_upper
                    severity = "EXTREME" if is_extreme else "MODERATE"
                    ident_val = str(df.loc[idx, id_col]) if id_col else f"Row {idx}"

                    outliers.append(OutlierItem(
                        column_name=col,
                        row_index=int(idx),
                        identifier=ident_val,
                        value=round(float(val), 2),
                        method="IQR",
                        lower_bound=lower_bound,
                        upper_bound=upper_bound,
                        severity=severity
                    ))

        return outliers
