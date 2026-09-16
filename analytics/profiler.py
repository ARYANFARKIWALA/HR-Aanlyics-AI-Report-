"""Statistical data profiler for query result sets."""


import pandas as pd

from .schemas import ColumnClassification, ColumnProfile


class DataProfiler:
    """Computes comprehensive summary statistics across all columns in a dataset."""

    @staticmethod
    def profile(df: pd.DataFrame, classifications: list[ColumnClassification]) -> list[ColumnProfile]:
        profiles = []
        total_rows = len(df)
        cls_map = {c.column_name: c.semantic_type for c in classifications}

        for col in df.columns:
            series = df[col]
            sem_type = cls_map.get(col, "CATEGORICAL")
            null_cnt = int(series.isna().sum())
            null_pct = round((null_cnt / max(total_rows, 1)) * 100, 2)
            unique_cnt = int(series.nunique(dropna=True))

            min_v = None
            max_v = None
            mean_v = None
            median_v = None
            std_v = None

            if pd.api.types.is_numeric_dtype(series):
                clean_s = series.dropna()
                if not clean_s.empty:
                    min_v = round(float(clean_s.min()), 2)
                    max_v = round(float(clean_s.max()), 2)
                    mean_v = round(float(clean_s.mean()), 2)
                    median_v = round(float(clean_s.median()), 2)
                    std_v = round(float(clean_s.std()), 2) if len(clean_s) > 1 else 0.0

            profiles.append(ColumnProfile(
                column_name=col,
                semantic_type=sem_type,
                dtype=str(series.dtype),
                null_count=null_cnt,
                null_pct=null_pct,
                unique_count=unique_cnt,
                min_val=min_v,
                max_val=max_v,
                mean_val=mean_v,
                median_val=median_v,
                std_val=std_v
            ))

        return profiles
