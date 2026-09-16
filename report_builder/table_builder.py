"""Table Builder for styled tabular reporting."""

from typing import Any

import pandas as pd

from .schemas import TableConfig


class TableBuilder:
    """Formats report data tables with sorting, column types, and conditional badges."""

    @classmethod
    def build_table(cls, df: pd.DataFrame, config: TableConfig) -> dict[str, Any]:
        if df.empty:
            return {
                "table_id": config.table_id,
                "title": config.title,
                "columns": [c.model_dump() for c in config.columns],
                "rows": [],
                "total_rows": 0
            }

        # Select only requested columns if they exist in df
        target_cols = [c.field for c in config.columns if c.field in df.columns]
        sub_df = df[target_cols].copy() if target_cols else df.copy()

        # Format values based on column config
        col_map = {c.field: c for c in config.columns}
        formatted_records = []

        for _, row in sub_df.iterrows():
            rec = {}
            for col in sub_df.columns:
                val = row[col]
                c_conf = col_map.get(col)
                if c_conf and pd.notna(val):
                    fmt = c_conf.format_type
                    if fmt == "currency" and isinstance(val, (int, float)):
                        rec[col] = f"${val:,.0f}"
                    elif fmt == "percentage" and isinstance(val, (int, float)):
                        rec[col] = f"{val:.1f}%"
                    else:
                        rec[col] = val
                else:
                    rec[col] = val if pd.notna(val) else ""
            formatted_records.append(rec)

        return {
            "table_id": config.table_id,
            "title": config.title,
            "columns": [c.model_dump() for c in config.columns],
            "rows": formatted_records[:config.page_size],
            "total_rows": len(formatted_records)
        }
