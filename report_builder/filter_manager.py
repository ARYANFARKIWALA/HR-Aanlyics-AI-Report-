"""Interactive global filter engine for report dashboards."""

from typing import Any

import pandas as pd

from .schemas import FilterConfig


class FilterManager:
    """Applies dynamic dashboard filter predicates across report datasets."""

    @classmethod
    def apply_filters(cls, df: pd.DataFrame, active_filters: dict[str, Any]) -> pd.DataFrame:
        if df.empty or not active_filters:
            return df

        filtered_df = df.copy()
        for field, value in active_filters.items():
            if field not in filtered_df.columns or value is None:
                continue

            if isinstance(value, list):
                if value:  # Non-empty list
                    filtered_df = filtered_df[filtered_df[field].isin(value)]
            elif isinstance(value, str):
                if value.strip() and value != "All":
                    filtered_df = filtered_df[filtered_df[field] == value]
            elif isinstance(value, (int, float)):
                filtered_df = filtered_df[filtered_df[field] == value]

        return filtered_df

    @classmethod
    def discover_filters(cls, df: pd.DataFrame) -> list[FilterConfig]:
        """Auto-discovers filter controls based on low-cardinality categorical columns."""
        filters: list[FilterConfig] = []
        if df.empty:
            return filters

        for col in df.columns:
            # Look for categorical columns with 2 to 30 unique values
            unique_cnt = df[col].nunique(dropna=True)
            if 2 <= unique_cnt <= 30:
                opts = sorted([str(v) for v in df[col].dropna().unique()])
                filters.append(FilterConfig(
                    field=col,
                    label=col.replace("_", " ").title(),
                    filter_type="multiselect",
                    options=opts,
                    default_value=None
                ))

        return filters
