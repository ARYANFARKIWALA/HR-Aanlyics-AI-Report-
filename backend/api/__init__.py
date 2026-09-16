"""API routers package."""
from .auth_routes import router as auth_router
from .query_routes import router as query_router
from .sql_repo_routes import router as sql_repo_router
from .rag_routes import router as rag_router
from .analytics_routes import router as analytics_router
from .report_routes import router as report_router
from .database_routes import router as database_router
from .sql_repository_routes import router as sql_repository_router
from .schema_routes import router as schema_router
from .business_rule_routes import router as business_rule_router
from .text_to_sql_routes import router as text_to_sql_router
from .sql_validator_routes import router as sql_validator_router
from .query_execution_routes import router as query_execution_router
from .report_builder_routes import router as report_builder_router
from .report_lifecycle_routes import router as report_lifecycle_router
from .evaluation_routes import router as evaluation_router

__all__ = [
    "auth_router",
    "query_router",
    "sql_repo_router",
    "rag_router",
    "analytics_router",
    "report_router",
    "database_router",
    "sql_repository_router",
    "schema_router",
    "business_rule_router",
    "text_to_sql_router",
    "sql_validator_router",
    "query_execution_router",
    "report_builder_router",
    "report_lifecycle_router",
    "evaluation_router",
]


