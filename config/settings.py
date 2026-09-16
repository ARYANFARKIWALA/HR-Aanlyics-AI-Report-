"""Configuration and Environment Settings for HR Analytics AI Report Builder."""

import os
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class AppSettings(BaseModel):
    """Strongly-typed production configuration system."""
    
    app_name: str = "HR-Analytics-AI-Report-Builder"
    app_version: str = "2.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("APP_ENV", os.getenv("ENV", "development")).lower())
    
    # Network Bindings
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    frontend_port: int = Field(default_factory=lambda: int(os.getenv("FRONTEND_PORT", "8501")))
    
    # Database Separation (Application Metadata vs HR Data Database)
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./hr_analytics.db"))
    app_database_url: Optional[str] = Field(default_factory=lambda: os.getenv("APP_DATABASE_URL", None))
    hr_database_url: Optional[str] = Field(default_factory=lambda: os.getenv("HR_DATABASE_URL", None))
    
    # Security & Authentication
    jwt_secret: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", os.getenv("JWT_SECRET", "hr_analytics_super_secret_jwt_key_2026_change_in_production")))
    jwt_algorithm: str = Field(default_factory=lambda: os.getenv("ALGORITHM", "HS256"))
    access_token_expire_minutes: int = Field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")))
    encryption_key: Optional[str] = Field(default_factory=lambda: os.getenv("ENCRYPTION_KEY", None))
    
    # AI & RAG Configuration
    ai_provider: str = Field(default_factory=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "gemini"))
    ai_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gemini-1.5-flash"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", None))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", None))
    vector_db_url: Optional[str] = Field(default_factory=lambda: os.getenv("VECTOR_DB_URL", None))
    
    # Query Execution & Safety Guardrails
    max_query_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("QUERY_TIMEOUT_SECONDS", "30")))
    max_result_rows: int = Field(default_factory=lambda: int(os.getenv("MAX_QUERY_ROW_LIMIT", "10000")))
    enforce_read_only: bool = Field(default_factory=lambda: os.getenv("ENFORCE_READ_ONLY", "True").lower() == "true")
    
    # Logging & Operational Monitoring
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    cors_origins: List[str] = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))

    def is_production(self) -> bool:
        return self.environment == EnvironmentType.PRODUCTION.value

    def is_testing(self) -> bool:
        return self.environment == EnvironmentType.TESTING.value

    def validate_for_startup(self) -> List[str]:
        """Performs fail-fast environment checks before application starts."""
        warnings_or_errors = []
        if self.is_production():
            if "change_in_production" in self.jwt_secret or len(self.jwt_secret) < 32:
                warnings_or_errors.append("PRODUCTION ERROR: Insecure JWT secret key configured. Must be >= 32 random characters.")
            if self.database_url.startswith("sqlite"):
                warnings_or_errors.append("PRODUCTION WARNING: SQLite database detected. PostgreSQL is strongly recommended for production concurrency.")
            if "*" in self.cors_origins:
                warnings_or_errors.append("PRODUCTION WARNING: Wildcard CORS ('*') configured in production environment.")
        return warnings_or_errors


# Global settings singleton
settings = AppSettings()
