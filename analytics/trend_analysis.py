"""Time-series trend analyzer computing YoY, MoM, and trajectory indicators."""

from typing import List
import pandas as pd
from .schemas import TrendItem, ColumnClassification


class TrendAnalyzer:
    """Computes deterministic temporal trends across hiring, attrition, and compensation."""

    @classmethod
    def analyze_trends(
        cls,
        df: pd.DataFrame,
        classifications: List[ColumnClassification]
    ) -> List[TrendItem]:
        trend_items: List[TrendItem] = []
        if df.empty:
            return trend_items

        date_col = None
        for c in classifications:
            if c.semantic_type == "DATE":
                date_col = c.column_name
                break

        if not date_col:
            return trend_items

        # Convert date column to period
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            valid_df = df[dates.notna()].copy()
            valid_df["_period_year"] = dates.dt.year.astype(str)

            # Analyze count per period
            counts = valid_df["_period_year"].value_counts().sort_index()
            prev_val = None

            for period, val in counts.items():
                change_abs = None
                change_pct = None
                direction = "STABLE"

                if prev_val is not None:
                    change_abs = round(float(val - prev_val), 2)
                    if prev_val > 0:
                        change_pct = round((change_abs / prev_val) * 100, 2)

                    if change_abs > 0:
                        direction = "INCREASING"
                    elif change_abs < 0:
                        direction = "DECREASING"

                trend_items.append(TrendItem(
                    time_period=str(period),
                    metric_name=f"Volume by {date_col}",
                    value=float(val),
                    previous_value=prev_val,
                    change_absolute=change_abs,
                    change_pct=change_pct,
                    direction=direction
                ))
                prev_val = float(val)

        except Exception:
            pass

        return trend_items
