"""Module 3: HR Metadata & Semantic Intelligence Mapper.

Provides heuristic, dictionary, and semantic mappings of database schemas to:
1. HR Business Entity Types (EMPLOYEE, DEPARTMENT, COMPENSATION, etc.)
2. Normalized Data Types
3. Metric vs Dimension Classifications with default aggregations
4. Date Roles (HIRE_DATE, TERMINATION_DATE, EFFECTIVE_DATE, etc.)
5. Compliance & Data Sensitivity Levels (FINANCIAL, PERSONAL_IDENTIFIER, etc.)
6. Effective Dating Pattern Detection
"""

import re
from typing import Dict, Any, Tuple, Optional, List


class HRMetadataMapper:
    """Semantic mapping engine for HR databases."""

    # Entity classification keywords
    ENTITY_PATTERNS = {
        "EMPLOYEE": [r"employ", r"staff", r"worker", r"person", r"headcount"],
        "DEPARTMENT": [r"department", r"dept", r"division", r"cost_center", r"business_unit"],
        "JOB_POSITION": [r"job", r"position", r"designation", r"role_profile", r"profile"],
        "COMPENSATION": [r"compensation", r"salary", r"pay_grade", r"wage", r"bonus", r"compa"],
        "PAYROLL": [r"payroll", r"payslip", r"paycheck", r"tax_deduction"],
        "PERFORMANCE": [r"performance", r"review", r"appraisal", r"goal", r"evaluation", r"rating"],
        "LEAVE_ATTENDANCE": [r"leave", r"absence", r"attendance", r"time_off", r"pto", r"timesheet"],
        "BENEFITS": [r"benefit", r"insurance", r"pension", r"healthcare"],
        "RECRUITMENT": [r"recruit", r"applicant", r"candidate", r"requisition", r"interview", r"job_offer"],
        "ORGANIZATION_UNIT": [r"organization", r"company", r"subsidiary", r"legal_entity"],
        "LOCATION": [r"location", r"office", r"branch", r"facility", r"site", r"country"],
    }

    # Common business definitions for HR columns
    COLUMN_DEFINITIONS = {
        "employee_number": "Unique organizational alphanumeric identifier assigned to each employee.",
        "first_name": "Legal given name of the worker.",
        "last_name": "Family name or surname of the worker.",
        "email": "Primary corporate or personal contact email address.",
        "gender": "Gender classification used for equal employment opportunity (EEO) reporting.",
        "ethnicity": "Self-reported demographic racial/ethnic background for diversity metrics.",
        "hire_date": "Calendar date the employee formally commenced active employment.",
        "termination_date": "Calendar date the worker officially separated from the organization.",
        "status": "Current employment operational state (e.g., Active, Terminated, On Leave).",
        "attrition_type": "Classification of separation (Voluntary vs Involuntary resignation/termination).",
        "attrition_reason": "Primary rationale documented for the employee's departure.",
        "employment_type": "Nature of employment contract (e.g., Full-Time, Part-Time, Contractor).",
        "work_location": "Primary geographic working arrangement (Remote, Hybrid, On-Site).",
        "effective_start_date": "The calendar date on which this historical/dated record became effective.",
        "effective_end_date": "The calendar date on which this record lapsed (e.g., 9999-12-31 if active).",
        "is_current": "Boolean flag indicating whether this record represents the employee's current state.",
        "base_salary": "Fixed annual or periodic base compensation before overtime, allowances, or bonuses.",
        "bonus": "Discretionary, performance, or contractual variable compensation paid.",
        "compa_ratio": "Comparative salary ratio: (Actual Base Salary / Midpoint of Job Profile Grade).",
        "change_reason": "Business justification for a compensation or title change event.",
        "rating": "Numerical performance assessment score awarded during an appraisal cycle.",
        "potential_score": "Nine-box grid assessment rating for leadership or career potential.",
        "goals_achieved_pct": "Percentage of assigned individual OKRs or performance milestones achieved.",
        "days_taken": "Total number of working days taken during an approved absence or leave request.",
        "leave_type": "Category of time-off taken (Annual, Sick, Parental, Bereavement, Unpaid).",
        "cost_center": "Financial accounting code responsible for departmental expenses and headcount.",
        "budget": "Approved total departmental annual operational expenditure budget.",
        "min_salary": "Lowest base salary permissible for the assigned job profile pay grade.",
        "mid_salary": "Market median compensation midpoint for the assigned job profile pay grade.",
        "max_salary": "Highest base salary permissible for the assigned job profile pay grade."
    }

    @classmethod
    def classify_table_entity(cls, table_name: str) -> str:
        """Determines the primary HR business entity type for a table."""
        tbl_clean = table_name.lower().strip()
        for entity, patterns in cls.ENTITY_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, tbl_clean):
                    return entity
        return "OTHER"

    @classmethod
    def generate_business_name(cls, technical_name: str) -> str:
        """Converts technical snake_case or camelCase names into clean business labels."""
        # Special replacements
        specials = {
            "id": "ID",
            "emp": "Employee",
            "dept": "Department",
            "fks": "Foreign Keys",
            "pk": "Primary Key",
            "fk": "Foreign Key",
            "pct": "%",
            "pto": "PTO",
            "okr": "OKR",
            "kpi": "KPI",
            "ssn": "SSN",
            "url": "URL",
            "dob": "Date of Birth",
        }
        
        # Replace underscores and split camelCase
        s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', technical_name)
        words = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).replace("-", "_").split("_")

        cleaned_words = []
        for w in words:
            wl = w.lower()
            if wl in specials:
                cleaned_words.append(specials[wl])
            elif wl == "compa" and "ratio" in [x.lower() for x in words]:
                cleaned_words.append("Compa")
            else:
                cleaned_words.append(w.capitalize())

        if technical_name.lower() in ["compa_ratio", "compa-ratio"]:
            return "Compa-Ratio"
        return " ".join(cleaned_words)


    @classmethod
    def normalize_data_type(cls, raw_type: str) -> str:
        """Normalizes vendor-specific SQL data types to standard categories."""
        rt = raw_type.upper()
        if any(x in rt for x in ["INT", "SERIAL", "SMALLINT", "TINYINT", "BIGINT"]):
            if "TINYINT(1)" in rt or "BOOL" in rt:
                return "BOOLEAN"
            return "INTEGER"
        if any(x in rt for x in ["FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC", "MONEY"]):
            return "DECIMAL"
        if any(x in rt for x in ["BOOL"]):
            return "BOOLEAN"
        if any(x in rt for x in ["DATE"]) and not any(x in rt for x in ["TIME"]):
            return "DATE"
        if any(x in rt for x in ["TIME", "TIMESTAMP"]):
            return "TIMESTAMP"
        if any(x in rt for x in ["CHAR", "TEXT", "VARCHAR", "STRING", "CLOB"]):
            return "STRING"
        if any(x in rt for x in ["JSON", "JSONB"]):
            return "JSON"
        return "OTHER"

    @classmethod
    def classify_column_semantics(
        cls,
        column_name: str,
        data_type: str,
        is_primary_key: bool = False,
        is_foreign_key: bool = False
    ) -> Dict[str, Any]:
        """Infers metric/dimension role, date role, sensitivity, and HR concept."""
        col_lower = column_name.lower().strip()
        norm_type = cls.normalize_data_type(data_type)

        # 1. Date Role
        is_date_field = norm_type in ["DATE", "TIMESTAMP"] or any(x in col_lower for x in ["_date", "date_", "_at", "_time"])
        date_role = "NONE"
        if is_date_field:
            if "hire" in col_lower:
                date_role = "HIRE_DATE"
            elif any(x in col_lower for x in ["term", "exit", "leaving", "separation"]):
                date_role = "TERMINATION_DATE"
            elif any(x in col_lower for x in ["start_date", "effective_start", "valid_from"]):
                date_role = "EFFECTIVE_DATE"
            elif any(x in col_lower for x in ["end_date", "effective_end", "valid_to", "expiry"]):
                date_role = "EXPIRY_DATE"
            elif any(x in col_lower for x in ["birth", "dob"]):
                date_role = "BIRTH_DATE"
            elif "review" in col_lower:
                date_role = "REVIEW_DATE"
            elif any(x in col_lower for x in ["pay", "payroll", "salary_date"]):
                date_role = "PAY_DATE"
            else:
                date_role = "TRANSACTION_DATE"

        # 2. Metric vs Dimension
        is_metric = False
        default_agg = "NONE"
        is_dimension = False

        if is_primary_key or is_foreign_key:
            is_dimension = True
            is_metric = False
        elif is_date_field:
            is_dimension = True
            is_metric = False
        elif norm_type in ["INTEGER", "DECIMAL"]:
            # Exclude ID or code-like integers
            if col_lower.endswith("_id") or col_lower.endswith("_no") or col_lower.endswith("_code"):
                is_dimension = True
            elif any(x in col_lower for x in ["salary", "bonus", "budget", "amount", "cost", "wage", "compensation"]):
                is_metric = True
                default_agg = "SUM"
            elif any(x in col_lower for x in ["ratio", "rating", "score", "pct", "percent", "average", "avg"]):
                is_metric = True
                default_agg = "AVG"
            elif any(x in col_lower for x in ["days", "hours", "count", "headcount", "quota"]):
                is_metric = True
                default_agg = "SUM"
            elif any(x in col_lower for x in ["min_", "minimum"]):
                is_metric = True
                default_agg = "MIN"
            elif any(x in col_lower for x in ["max_", "maximum"]):
                is_metric = True
                default_agg = "MAX"
            else:
                is_metric = True
                default_agg = "SUM"
        elif norm_type in ["STRING", "BOOLEAN"]:
            is_dimension = True

        # 3. Sensitivity Classification
        is_sensitive = False
        sensitive_category = "NONE"

        if any(x in col_lower for x in ["salary", "bonus", "compensation", "wage", "bank", "account_no", "pay_rate"]):
            is_sensitive = True
            sensitive_category = "FINANCIAL"
        elif any(x in col_lower for x in ["ssn", "social_security", "national_id", "passport", "tax_id", "phone", "mobile", "address", "email"]):
            is_sensitive = True
            sensitive_category = "PERSONAL_IDENTIFIER"
        elif any(x in col_lower for x in ["disability", "medical", "health", "diagnosis"]):
            is_sensitive = True
            sensitive_category = "HEALTH"
        elif any(x in col_lower for x in ["termination_reason", "disciplinary", "rating_notes", "feedback"]):
            is_sensitive = True
            sensitive_category = "RESTRICTED"
        elif any(x in col_lower for x in ["first_name", "last_name", "work_location", "department_id"]):
            is_sensitive = False
            sensitive_category = "PUBLIC_INTERNAL"

        # 4. Definition & Concept
        definition = cls.COLUMN_DEFINITIONS.get(col_lower)
        if not definition:
            if is_primary_key:
                definition = f"Primary unique identifier for records in this table."
            elif is_foreign_key:
                definition = f"Foreign key reference link to related entity."
            elif is_metric:
                definition = f"Quantitative measure of {col_lower.replace('_', ' ')}."
            else:
                definition = f"Descriptive attribute specifying {col_lower.replace('_', ' ')}."

        return {
            "normalized_data_type": norm_type,
            "is_metric": is_metric,
            "default_aggregation": default_agg,
            "is_dimension": is_dimension,
            "is_date_field": is_date_field,
            "date_role": date_role,
            "is_sensitive": is_sensitive,
            "sensitive_category": sensitive_category,
            "business_definition": definition,
            "hr_concept": cls._infer_hr_concept(col_lower, is_metric, is_date_field)
        }

    @classmethod
    def _infer_hr_concept(cls, col_lower: str, is_metric: bool, is_date_field: bool) -> str:
        """Maps column name to a canonical HR concept taxonomy."""
        if "emp" in col_lower and ("no" in col_lower or "id" in col_lower):
            return "EMPLOYEE_IDENTIFIER"
        if "salary" in col_lower or "wage" in col_lower:
            return "BASE_COMPENSATION"
        if "bonus" in col_lower:
            return "VARIABLE_COMPENSATION"
        if "compa" in col_lower:
            return "PAY_PARITY_RATIO"
        if "hire" in col_lower:
            return "TENURE_COMMENCEMENT"
        if "term" in col_lower or "attrition" in col_lower:
            return "ATTRITION_METRIC"
        if "dept" in col_lower:
            return "ORGANIZATIONAL_HIERARCHY"
        if "leave" in col_lower or "pto" in col_lower or "absence" in col_lower:
            return "TIME_AND_ATTENDANCE"
        if "review" in col_lower or "rating" in col_lower:
            return "TALENT_ASSESSMENT"
        if is_date_field:
            return "TEMPORAL_MARKER"
        if is_metric:
            return "QUANTITATIVE_KPI"
        return "DIMENSIONAL_ATTRIBUTE"

    @classmethod
    def detect_effective_dating(cls, column_names: List[str]) -> bool:
        """Detects whether a table employs effective dating conventions."""
        cols = [c.lower() for c in column_names]
        has_start = any(x in cols for x in ["effective_start_date", "valid_from", "effective_date"])
        has_end = any(x in cols for x in ["effective_end_date", "valid_to", "is_current"])
        return has_start and has_end
