"""Column semantic type classifier for HR datasets."""

import pandas as pd

from .schemas import ColumnClassification

CURRENCY_KEYWORDS = {"salary", "base_salary", "compensation", "comp", "bonus", "budget", "payroll", "pay"}
DATE_KEYWORDS = {"date", "hire_date", "termination_date", "start_date", "end_date", "created_at", "updated_at", "timestamp"}
IDENTIFIER_KEYWORDS = {"id", "employee_id", "employee_number", "code", "ssn", "tax_id", "uuid"}
CATEGORICAL_KEYWORDS = {"department", "dept", "job_family", "gender", "ethnicity", "status", "location", "work_location", "salary_grade", "role", "title", "attrition_type"}


class ColumnClassifier:
    """Classifies DataFrame columns into semantic reporting types."""

    @classmethod
    def classify(cls, df: pd.DataFrame) -> list[ColumnClassification]:
        classifications = []
        for col in df.columns:
            col_lower = str(col).lower()
            series = df[col]

            # 1. Identifier
            if col_lower in IDENTIFIER_KEYWORDS or col_lower.endswith(("_id", "_number")):
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="IDENTIFIER",
                    is_dimension=False,
                    is_metric=False
                ))
            # 2. Boolean
            elif pd.api.types.is_bool_dtype(series) or col_lower.startswith(("is_", "has_")):
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="BOOLEAN",
                    is_dimension=True,
                    is_metric=False
                ))
            # 3. Ratio, Percentage, Rate, or Rating (Numeric Metric)
            elif any(k in col_lower for k in ["ratio", "rate", "pct", "percent", "score", "rating"]):
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="NUMERIC",
                    is_dimension=False,
                    is_metric=True
                ))
            # 4. Currency
            elif any(k in col_lower for k in CURRENCY_KEYWORDS):
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="CURRENCY",
                    is_dimension=False,
                    is_metric=True
                ))
            # 4. Date
            elif pd.api.types.is_datetime64_any_dtype(series) or any(k in col_lower for k in DATE_KEYWORDS):
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="DATE",
                    is_dimension=True,
                    is_metric=False
                ))
            # 5. Numeric Metric
            elif pd.api.types.is_numeric_dtype(series):
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="NUMERIC",
                    is_dimension=False,
                    is_metric=True
                ))
            # 6. Categorical Dimension
            else:
                classifications.append(ColumnClassification(
                    column_name=col,
                    semantic_type="CATEGORICAL",
                    is_dimension=True,
                    is_metric=False
                ))

        return classifications
