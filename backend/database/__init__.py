"""Database module initialization."""
from .connection import Base, engine, get_db, init_db, SessionLocal
from .models import (
    User,
    Department,
    JobProfile,
    Employee,
    CompensationHistory,
    PerformanceReview,
    LeaveRecord,
    SQLRepository,
    AuditLog,
)
from .models_repo import (
    SQLReport,
    SQLReportMetadata,
    SQLReportParameter,
    SQLReportVersion,
    SQLApproval,
    SQLCategory,
    Tag,
    SQLReportTag,
)
from .models_schema import (
    SchemaTable,
    SchemaColumn,
    SchemaRelationship,
    SchemaIndex,
    SchemaConstraint,
    SchemaSnapshot,
    SchemaChange,
    SchemaUsageMetric,
)
from .models_rules import (
    BusinessRule,
    BusinessRuleVersion,
    BusinessRuleAudit,
    RuleDependency,
    ReportBusinessRule,
    RuleTable,
    RuleColumn,
)
from .models_rag import (
    RAGDocument,
    RAGChunk,
)
from .models_auth import (
    Organization,
    Role,
    Permission,
    RolePermission,
    UserDatabaseAccess,
    ColumnPermission,
    RowAccessRule,
    UserSession,
    SecurityAuditLog,
)
from .models_validation import (
    SQLValidationAuditLog,
)
from .models_execution import (
    QueryExecutionAuditLog,
)
from .models_analytics import (
    AnalyticsAuditLog,
)
from .models_reports import (
    SavedReport,
    SavedReportVersion,
    ReportAccess,
    ReportExecutionRecord,
)

__all__ = [
    "Base",
    "engine",
    "get_db",
    "init_db",
    "SessionLocal",
    "User",
    "Department",
    "JobProfile",
    "Employee",
    "CompensationHistory",
    "PerformanceReview",
    "LeaveRecord",
    "SQLRepository",
    "AuditLog",
    "SQLReport",
    "SQLReportMetadata",
    "SQLReportParameter",
    "SQLReportVersion",
    "SQLApproval",
    "SQLCategory",
    "Tag",
    "SQLReportTag",
    "SchemaTable",
    "SchemaColumn",
    "SchemaRelationship",
    "SchemaIndex",
    "SchemaConstraint",
    "SchemaSnapshot",
    "SchemaChange",
    "SchemaUsageMetric",
    "BusinessRule",
    "BusinessRuleVersion",
    "BusinessRuleAudit",
    "RuleDependency",
    "ReportBusinessRule",
    "RuleTable",
    "RuleColumn",
    "RAGDocument",
    "RAGChunk",
    "Organization",
    "Role",
    "Permission",
    "RolePermission",
    "UserDatabaseAccess",
    "ColumnPermission",
    "RowAccessRule",
    "UserSession",
    "SecurityAuditLog",
    "SQLValidationAuditLog",
    "QueryExecutionAuditLog",
    "AnalyticsAuditLog",
    "SavedReport",
    "SavedReportVersion",
    "ReportAccess",
    "ReportExecutionRecord",
]


