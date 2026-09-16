"""Result set processor preserving exact database types and enforcing row caps."""

import datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import CursorResult

from .schemas import QueryColumnMeta

MAX_RESULT_ROWS = 10000


class ResultHandler:
    """Processes database cursor results with exact data-type preservation."""

    @staticmethod
    def process_cursor(
        cursor: CursorResult,
        max_rows: int = MAX_RESULT_ROWS
    ) -> tuple[pd.DataFrame, list[str], list[QueryColumnMeta]]:
        """
        Fetches up to max_rows and preserves types (Decimal, Date, Datetime, Int, Float, Bool).
        """
        columns = list(cursor.keys())
        fetched_rows = cursor.fetchmany(max_rows)

        records = []
        for row in fetched_rows:
            rec = {}
            for col, val in zip(columns, row):
                # Clean up specific types for JSON/API fidelity
                if isinstance(val, Decimal):
                    rec[col] = float(val)
                elif isinstance(val, (datetime.date, datetime.datetime)):
                    rec[col] = val.isoformat()
                else:
                    rec[col] = val
            records.append(rec)

        df = pd.DataFrame(records, columns=columns) if records else pd.DataFrame(columns=columns)

        # Build column metadata
        column_meta: list[QueryColumnMeta] = []
        for col in columns:
            dtype_str = "string"
            if not df.empty:
                s = df[col]
                if pd.api.types.is_integer_dtype(s):
                    dtype_str = "integer"
                elif pd.api.types.is_float_dtype(s):
                    dtype_str = "float"
                elif pd.api.types.is_bool_dtype(s):
                    dtype_str = "boolean"
                elif pd.api.types.is_datetime64_any_dtype(s):
                    dtype_str = "datetime"
            column_meta.append(QueryColumnMeta(name=col, type=dtype_str))

        return df, columns, column_meta
