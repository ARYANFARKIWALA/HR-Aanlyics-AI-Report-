"""Executive KPI Card Builder with formatting and deltas."""

import pandas as pd

from .schemas import BuiltKPICard, KPICardConfig


class KPIBuilder:
    """Calculates formatted KPI metrics for executive dashboard scorecards."""

    @classmethod
    def build_kpi(cls, df: pd.DataFrame, config: KPICardConfig) -> BuiltKPICard:
        if df.empty:
            return BuiltKPICard(
                card_id=config.card_id,
                title=config.title,
                value="—",
                raw_value=0.0,
                delta_text=None,
                help_text=config.help_text
            )

        col = config.metric_field
        raw_val = 0.0

        # Calculate raw aggregated value
        if config.aggregation == "count":
            raw_val = float(len(df) if col == "*" or col not in df.columns else df[col].count())
        elif col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if not s.empty:
                if config.aggregation == "sum":
                    raw_val = float(s.sum())
                elif config.aggregation == "avg":
                    raw_val = float(s.mean())
                elif config.aggregation == "median":
                    raw_val = float(s.median())
                elif config.aggregation == "min":
                    raw_val = float(s.min())
                elif config.aggregation == "max":
                    raw_val = float(s.max())
                elif config.aggregation == "percentage":
                    # Percentage of rows meeting condition or mean * 100
                    raw_val = float(s.mean() * 100)

        # Format string
        fmt = config.format_type
        if fmt == "currency":
            val_str = f"${raw_val:,.0f}" if raw_val >= 1000 else f"${raw_val:,.2f}"
        elif fmt == "percentage":
            val_str = f"{raw_val:.1f}%"
        elif fmt == "integer":
            val_str = f"{round(raw_val):,}"
        elif fmt == "decimal":
            val_str = f"{raw_val:.2f}"
        else:
            val_str = f"{config.prefix}{raw_val}{config.suffix}"

        return BuiltKPICard(
            card_id=config.card_id,
            title=config.title,
            value=val_str,
            raw_value=round(raw_val, 2),
            delta_text=config.delta_text,
            delta_color=config.delta_color,
            help_text=config.help_text
        )
