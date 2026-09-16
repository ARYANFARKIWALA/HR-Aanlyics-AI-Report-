"""Reusable HR Analytics Services Engine (Module 9).

Provides robust, production-grade statistical and organizational HR calculations
using Pandas without altering raw query results without documentation.
"""

from typing import Any

import numpy as np
import pandas as pd


class HRAnalyticsEngine:
    """Core analytical calculation engine for enterprise HR metrics."""

    @staticmethod
    def calculate_totals(df: pd.DataFrame, column: str) -> dict[str, Any]:
        """Calculates sum total for numeric column."""
        if column not in df.columns or df.empty:
            return {"metric": "total", "column": column, "value": 0.0, "transformation": "none"}
        total_val = float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())
        return {
            "metric": "total",
            "column": column,
            "value": round(total_val, 2),
            "transformation": f"Sum of numeric column '{column}'"
        }

    @staticmethod
    def calculate_averages(df: pd.DataFrame, column: str) -> dict[str, Any]:
        """Calculates arithmetic mean for numeric column."""
        if column not in df.columns or df.empty:
            return {"metric": "average", "column": column, "value": 0.0, "transformation": "none"}
        avg_val = float(pd.to_numeric(df[column], errors="coerce").mean())
        return {
            "metric": "average",
            "column": column,
            "value": round(avg_val, 2) if not np.isnan(avg_val) else 0.0,
            "transformation": f"Mean calculation over '{column}'"
        }

    @staticmethod
    def calculate_percentages(
        df: pd.DataFrame,
        dimension_col: str,
        metric_col: str | None = None
    ) -> pd.DataFrame:
        """Calculates percentage composition across categories."""
        res_df = df.copy()
        if df.empty or dimension_col not in df.columns:
            return res_df

        if metric_col and metric_col in df.columns:
            total_sum = res_df[metric_col].sum()
            res_df["percentage"] = (res_df[metric_col] / total_sum * 100).round(2) if total_sum > 0 else 0.0
        else:
            counts = res_df[dimension_col].value_counts(normalize=True) * 100
            res_df["percentage"] = res_df[dimension_col].map(counts).round(2)

        return res_df

    @staticmethod
    def calculate_ratios(
        df: pd.DataFrame,
        numerator_col: str,
        denominator_col: str,
        ratio_col_name: str = "ratio"
    ) -> pd.DataFrame:
        """Calculates ratios between two metrics with zero-division guard."""
        res_df = df.copy()
        if numerator_col in df.columns and denominator_col in df.columns:
            num = pd.to_numeric(res_df[numerator_col], errors="coerce").fillna(0)
            den = pd.to_numeric(res_df[denominator_col], errors="coerce").fillna(0)
            res_df[ratio_col_name] = np.where(den > 0, (num / den).round(4), 0.0)
        return res_df

    @staticmethod
    def calculate_trends(
        df: pd.DataFrame,
        date_col: str,
        metric_col: str
    ) -> list[dict[str, Any]]:
        """Calculates period-over-period trend analysis."""
        trends = []
        if df.empty or date_col not in df.columns or metric_col not in df.columns:
            return trends

        sorted_df = df.sort_values(by=date_col)
        prev_val = None

        for _, row in sorted_df.iterrows():
            curr_val = float(row[metric_col]) if pd.notnull(row[metric_col]) else 0.0
            change_abs = round(curr_val - prev_val, 2) if prev_val is not None else 0.0
            change_pct = round((change_abs / prev_val * 100), 2) if prev_val and prev_val > 0 else 0.0
            direction = "INCREASING" if change_abs > 0 else ("DECREASING" if change_abs < 0 else "STABLE")

            trends.append({
                "time_period": str(row[date_col]),
                "metric_name": metric_col,
                "value": curr_val,
                "previous_value": prev_val,
                "change_absolute": change_abs,
                "change_pct": change_pct,
                "direction": direction
            })
            prev_val = curr_val

        return trends

    @staticmethod
    def calculate_ranking(
        df: pd.DataFrame,
        metric_col: str,
        ascending: bool = False,
        rank_col_name: str = "rank"
    ) -> pd.DataFrame:
        """Adds ordinal ranking by metric."""
        res_df = df.copy()
        if metric_col in df.columns and not df.empty:
            res_df[rank_col_name] = res_df[metric_col].rank(ascending=ascending, method="min").astype(int)
            res_df = res_df.sort_values(by=rank_col_name)
        return res_df

    @staticmethod
    def calculate_group_analysis(
        df: pd.DataFrame,
        group_cols: list[str],
        agg_dict: dict[str, Any]
    ) -> pd.DataFrame:
        """Performs multi-dimensional group aggregation."""
        if df.empty or not all(c in df.columns for c in group_cols):
            return df.copy()
        return df.groupby(group_cols, as_index=False).agg(agg_dict)

    @staticmethod
    def calculate_timeseries_analysis(
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        freq: str = "ME"
    ) -> pd.DataFrame:
        """Resamples and aggregates time series metrics."""
        if df.empty or date_col not in df.columns or metric_col not in df.columns:
            return df.copy()

        temp_df = df.copy()
        temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
        temp_df = temp_df.dropna(subset=[date_col])
        temp_df = temp_df.set_index(date_col)
        resampled = temp_df[metric_col].resample(freq).sum().reset_index()
        return resampled

    @staticmethod
    def calculate_growth_rate(
        df: pd.DataFrame,
        date_col: str,
        metric_col: str
    ) -> pd.DataFrame:
        """Calculates compound growth rate across chronological periods."""
        res_df = df.copy()
        if date_col in res_df.columns and metric_col in res_df.columns and not res_df.empty:
            res_df = res_df.sort_values(by=date_col)
            res_df["growth_rate_pct"] = res_df[metric_col].pct_change().fillna(0).round(4) * 100
        return res_df

    @staticmethod
    def calculate_headcount(
        df: pd.DataFrame,
        status_col: str | None = "status",
        active_val: str = "Active"
    ) -> dict[str, Any]:
        """Calculates total, active, and terminated headcount counts."""
        total = len(df)
        if status_col and status_col in df.columns:
            active = int((df[status_col].str.lower() == active_val.lower()).sum())
            terminated = int((df[status_col].str.lower() == "terminated").sum())
        else:
            active = total
            terminated = 0

        return {
            "total_records": total,
            "active_headcount": active,
            "terminated_headcount": terminated,
            "transformation": f"Counted status values in '{status_col}'" if status_col else "Row count"
        }

    @staticmethod
    def calculate_attrition_rate(
        df: pd.DataFrame,
        status_col: str = "status",
        active_val: str = "Active",
        terminated_val: str = "Terminated"
    ) -> dict[str, Any]:
        """Calculates organizational attrition percentage."""
        if df.empty or status_col not in df.columns:
            return {"attrition_rate_pct": 0.0, "retention_rate_pct": 100.0, "transformation": "none"}

        s = df[status_col].astype(str).str.lower()
        terminated = int((s == terminated_val.lower()).sum())
        total = len(df)
        rate = round((terminated / total * 100), 2) if total > 0 else 0.0
        return {
            "terminated_count": terminated,
            "total_headcount": total,
            "attrition_rate_pct": rate,
            "retention_rate_pct": round(100.0 - rate, 2),
            "transformation": f"Attrition formula: ({terminated} terminated / {total} total) * 100"
        }

    @staticmethod
    def calculate_turnover(
        df: pd.DataFrame,
        status_col: str = "status",
        terminated_val: str = "Terminated"
    ) -> dict[str, Any]:
        """Calculates turnover counts and proportions."""
        return HRAnalyticsEngine.calculate_attrition_rate(
            df=df,
            status_col=status_col,
            terminated_val=terminated_val
        )

    @staticmethod
    def calculate_tenure(
        df: pd.DataFrame,
        hire_date_col: str = "hire_date",
        termination_date_col: str | None = "termination_date"
    ) -> dict[str, Any]:
        """Calculates tenure statistics in years."""
        if df.empty or hire_date_col not in df.columns:
            return {"avg_tenure_years": 0.0, "median_tenure_years": 0.0, "transformation": "none"}

        hires = pd.to_datetime(df[hire_date_col], errors="coerce")
        now = pd.Timestamp.now()

        if termination_date_col and termination_date_col in df.columns:
            ends = pd.to_datetime(df[termination_date_col], errors="coerce").fillna(now)
        else:
            ends = pd.Series([now] * len(df), index=df.index)

        tenure_days = (ends - hires).dt.days
        tenure_years = tenure_days / 365.25
        tenure_clean = tenure_years.dropna()

        avg_tenure = float(tenure_clean.mean()) if not tenure_clean.empty else 0.0
        median_tenure = float(tenure_clean.median()) if not tenure_clean.empty else 0.0

        return {
            "avg_tenure_years": round(avg_tenure, 2),
            "median_tenure_years": round(median_tenure, 2),
            "min_tenure_years": round(float(tenure_clean.min()), 2) if not tenure_clean.empty else 0.0,
            "max_tenure_years": round(float(tenure_clean.max()), 2) if not tenure_clean.empty else 0.0,
            "transformation": f"Computed delta between '{hire_date_col}' and termination/current date"
        }

    @staticmethod
    def recommend_visualizations(df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Recommends charts based on canonical mapping rules:
        - Time series -> Line chart
        - Department comparison -> Bar chart
        - Distribution -> Histogram
        - Composition -> Pie/Donut
        - KPI -> Metric card
        """
        recommendations = []
        cols = list(df.columns)
        date_cols = [c for c in cols if any(k in c.lower() for k in ["date", "month", "year", "period", "quarter", "day"])]
        dept_cols = [c for c in cols if any(k in c.lower() for k in ["department", "dept", "org", "division", "team"])]

        if not df.empty:
            cat_cols = [c for c in cols if df[c].dtype == "object" and c not in date_cols]
            num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        else:
            cat_cols = [c for c in cols if c not in date_cols and not any(k in c.lower() for k in ["count", "sum", "avg", "salary", "budget", "rate", "ratio", "num", "attrition"])]
            num_cols = [c for c in cols if any(k in c.lower() for k in ["count", "sum", "avg", "salary", "budget", "rate", "ratio", "num", "attrition"])]

        # 1. KPI -> Metric Card (Always recommend for aggregate / summary cards)
        for num in num_cols[:2]:
            total = float(df[num].sum()) if not df.empty else 0.0
            recommendations.append({
                "chart_type": "metric_card",
                "title": f"Total {num.replace('_', ' ').title()}",
                "value": round(total, 2),
                "metric_name": num,
                "description": f"Executive summary metric card for {num}."
            })

        # 2. Time series -> Line chart
        if date_cols and num_cols:
            recommendations.append({
                "chart_type": "line",
                "title": f"Time Series: {num_cols[0]} over {date_cols[0]}",
                "x_axis": date_cols[0],
                "y_axis": num_cols[0],
                "description": "Chronological line trend tracking trajectory across periods."
            })

        # 3. Department comparison -> Bar chart
        target_cat = dept_cols[0] if dept_cols else (cat_cols[0] if cat_cols else None)
        if target_cat and num_cols:
            recommendations.append({
                "chart_type": "bar",
                "title": f"Department Comparison: {num_cols[0]} by {target_cat}",
                "x_axis": target_cat,
                "y_axis": num_cols[0],
                "description": f"Categorical comparative bar chart comparing segments of {target_cat}."
            })

        # 4. Distribution -> Histogram
        if num_cols:
            recommendations.append({
                "chart_type": "histogram",
                "title": f"Distribution Analysis: {num_cols[0]}",
                "x_axis": num_cols[0],
                "description": f"Frequency distribution histogram visualizing spread and variance for {num_cols[0]}."
            })

        # 5. Composition -> Pie / Donut
        if target_cat:
            recommendations.append({
                "chart_type": "pie",
                "title": f"Composition Breakdown: {target_cat}",
                "x_axis": target_cat,
                "description": f"Proportional composition donut/pie chart across {target_cat} segments."
            })

        return recommendations
