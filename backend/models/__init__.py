"""ORM Data Models package re-exporting database entities."""

from backend.database.connection import Base
from backend.database.models import (
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
from backend.database.models_analytics import (
    AnalyticsAuditLog,
)
from backend.database.models_auth import (
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
from backend.database.models_execution import (
    QueryExecutionAuditLog,
)
from backend.database.models_rag import (
    RAGChunk,
    RAGDocument,
)
from backend.database.models_repo import (
    SQLApproval,
    SQLCategory,
    SQLReport,
    SQLReportMetadata,
    SQLReportParameter,
    SQLReportTag,
    SQLReportVersion,
    Tag,
)
from backend.database.models_reports import (
    ReportAccess,
    ReportExecutionRecord,
    SavedReport,
    SavedReportVersion,
)
from backend.database.models_rules import (
    BusinessRule,
    BusinessRuleAudit,
    BusinessRuleVersion,
    ReportBusinessRule,
    RuleColumn,
    RuleDependency,
    RuleTable,
)
from backend.database.models_schema import (
    SchemaChange,
    SchemaColumn,
    SchemaConstraint,
    SchemaIndex,
    SchemaRelationship,
    SchemaSnapshot,
    SchemaTable,
    SchemaUsageMetric,
)
from backend.database.models_validation import (
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
    "Tag",
    "User",
    "UserDatabaseAccess",
    "UserSession",
]
