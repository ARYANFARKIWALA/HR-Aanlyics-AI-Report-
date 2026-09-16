"""Multidimensional segmentation and cohort slicing engine."""

from typing import List, Dict, Any
import pandas as pd
from .schemas import SegmentationBreakdown, ColumnClassification


class SegmentationEngine:
    """Slices HR metrics across organizational dimensions."""

    @classmethod
    def segment(
        cls,
        df: pd.DataFrame,
        classifications: List[ColumnClassification]
    ) -> List[SegmentationBreakdown]:
        breakdowns: List[SegmentationBreakdown] = []
        if df.empty:
            return breakdowns

        dim_cols = [c.column_name for c in classifications if c.semantic_type in ["CATEGORICAL", "BOOLEAN"]]
        metric_cols = [c.column_name for c in classifications if c.semantic_type in ["NUMERIC", "CURRENCY"]]

        # Limit to top 3 dimensions to keep responses focused
        target_dims = dim_cols[:3]

        for dim in target_dims:
            segments: Dict[str, Dict[str, Any]] = {}
            grouped = df.groupby(dim, observed=True)

            for group_name, group_df in grouped:
                seg_data: Dict[str, Any] = {"headcount": int(len(group_df))}

                for m in metric_cols[:2]:
                    s = pd.to_numeric(group_df[m], errors="coerce").dropna()
                    if not s.empty:
                        seg_data[f"avg_{m}"] = round(float(s.mean()), 2)
                        seg_data[f"median_{m}"] = round(float(s.median()), 2)

                segments[str(group_name)] = seg_data

            breakdowns.append(SegmentationBreakdown(
                dimension=dim,
                segments=segments
            ))

        return breakdowns
