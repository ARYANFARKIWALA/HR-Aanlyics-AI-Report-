"""ORM Data Models package re-exporting database entities."""

from backend.database.connection import Base
from backend.database.models import (
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
from backend.database.models_repo import (
    SQLReport,
    SQLReportMetadata,
    SQLReportParameter,
    SQLReportVersion,
    SQLApproval,
    SQLCategory,
    Tag,
    SQLReportTag,
)
from backend.database.models_schema import (
    SchemaTable,
    SchemaColumn,
    SchemaRelationship,
    SchemaIndex,
    SchemaConstraint,
    SchemaSnapshot,
    SchemaChange,
    SchemaUsageMetric,
)
from backend.database.models_rules import (
    BusinessRule,
    BusinessRuleVersion,
    BusinessRuleAudit,
    RuleDependency,
    ReportBusinessRule,
    RuleTable,
    RuleColumn,
)
from backend.database.models_rag import (
    RAGDocument,
    RAGChunk,
)
from backend.database.models_auth import (
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
from backend.database.models_validation import (
    SQLValidationAuditLog,
)
from backend.database.models_execution import (
    QueryExecutionAuditLog,
)
from backend.database.models_analytics import (
    AnalyticsAuditLog,
)
from backend.database.models_reports import (
    SavedReport,
    SavedReportVersion,
    ReportAccess,
    ReportExecutionRecord,
)

__all__ = [
    "Base",
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
