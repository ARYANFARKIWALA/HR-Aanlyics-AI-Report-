"""Bivariate Pearson and Spearman correlation analyzer."""


import pandas as pd

from .schemas import ColumnClassification, CorrelationItem


class CorrelationAnalyzer:
    """Computes statistical relationships between numeric HR dimensions."""

    @classmethod
    def analyze_correlations(
        cls,
        df: pd.DataFrame,
        classifications: list[ColumnClassification]
    ) -> list[CorrelationItem]:
        items: list[CorrelationItem] = []
        metric_cols = [c.column_name for c in classifications if c.semantic_type in ["NUMERIC", "CURRENCY"]]

        if len(metric_cols) < 2 or len(df) < 5:
            return items

        numeric_df = df[metric_cols].apply(pd.to_numeric, errors="coerce")
        corr_matrix = numeric_df.corr(method="pearson")

        seen_pairs = set()
        for col_a in metric_cols:
            for col_b in metric_cols:
                if col_a == col_b:
                    continue
                pair_key = tuple(sorted([col_a, col_b]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                coef = corr_matrix.loc[col_a, col_b]
                if pd.isna(coef):
                    continue

                coef_val = round(float(coef), 3)
                abs_coef = abs(coef_val)

                if abs_coef >= 0.7:
                    strength = "STRONG"
                elif abs_coef >= 0.4:
                    strength = "MODERATE"
                else:
                    strength = "WEAK"

                direction = "positive" if coef_val > 0 else "negative"
                interp = f"{strength.title()} {direction} correlation ({coef_val}) between {col_a} and {col_b}."

                items.append(CorrelationItem(
                    column_a=col_a,
                    column_b=col_b,
                    correlation_coefficient=coef_val,
                    strength=strength,
                    interpretation=interp
                ))

        # Sort by absolute strength
        items.sort(key=lambda x: abs(x.correlation_coefficient), reverse=True)
        return items
