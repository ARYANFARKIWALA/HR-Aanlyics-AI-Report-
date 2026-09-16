"""Database module initialization."""
from .connection import Base, SessionLocal, engine, get_db, init_db
from .models import (
    AuditLog,
    CompensationHistory,
    Department,
    Employee,
    JobProfile,
    LeaveRecord,
    PerformanceReview,
    SQLRepository,
    User,
)
from .models_analytics import (
    AnalyticsAuditLog,
)
from .models_auth import (
    ColumnPermission,
    Organization,
    Permission,
    Role,
    RolePermission,
    RowAccessRule,
    SecurityAuditLog,
    UserDatabaseAccess,
    UserSession,
)
from .models_execution import (
    QueryExecutionAuditLog,
)
from .models_rag import (
    RAGChunk,
    RAGDocument,
)
from .models_repo import (
    SQLApproval,
    SQLCategory,
    SQLReport,
    SQLReportMetadata,
    SQLReportParameter,
    SQLReportTag,
    SQLReportVersion,
    Tag,
)
from .models_reports import (
    ReportAccess,
    ReportExecutionRecord,
    SavedReport,
    SavedReportVersion,
)
from .models_rules import (
    BusinessRule,
    BusinessRuleAudit,
    BusinessRuleVersion,
    ReportBusinessRule,
    RuleColumn,
    RuleDependency,
    RuleTable,
)
from .models_schema import (
    SchemaChange,
    SchemaColumn,
    SchemaConstraint,
    SchemaIndex,
    SchemaRelationship,
    SchemaSnapshot,
    SchemaTable,
    SchemaUsageMetric,
)
from .models_validation import (
    SQLValidationAuditLog,
)

__all__ = [
    "AnalyticsAuditLog",
    "AuditLog",
    "Base",
    "BusinessRule",
    "BusinessRuleAudit",
    "BusinessRuleVersion",
    "ColumnPermission",
    "CompensationHistory",
    "Department",
    "Employee",
    "JobProfile",
    "LeaveRecord",
    "Organization",
    "PerformanceReview",
    "Permission",
    "QueryExecutionAuditLog",
    "RAGChunk",
    "RAGDocument",
    "ReportAccess",
    "ReportBusinessRule",
    "ReportExecutionRecord",
    "Role",
    "RolePermission",
    "RowAccessRule",
    "RuleColumn",
    "RuleDependency",
    "RuleTable",
    "SQLApproval",
    "SQLCategory",
    "SQLReport",
    "SQLReportMetadata",
    "SQLReportParameter",
    "SQLReportTag",
    "SQLReportVersion",
    "SQLRepository",
    "SQLValidationAuditLog",
    "SavedReport",
    "SavedReportVersion",
    "SchemaChange",
    "SchemaColumn",
    "SchemaConstraint",
    "SchemaIndex",
    "SchemaRelationship",
    "SchemaSnapshot",
    "SchemaTable",
    "SchemaUsageMetric",
    "SecurityAuditLog",
    "SessionLocal",
    "Tag",
    "User",
    "UserDatabaseAccess",
    "UserSession",
    "engine",
    "get_db",
    "init_db",
]


