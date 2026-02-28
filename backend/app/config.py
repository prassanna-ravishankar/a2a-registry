"""Configuration management using pydantic-settings"""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database - individual components (used in Kubernetes)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "a2a_registry"
    db_user: str = "postgres"
    db_password: str = ""

    # Database URL (optional override, takes precedence if set)
    database_url_override: str = ""

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct DATABASE_URL from components or use override"""
        if self.database_url_override:
            return self.database_url_override
        if self.db_password:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return f"postgresql://{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}"
    database_pool_min_size: int = 5
    database_pool_max_size: int = 20

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "https://www.a2aregistry.org"]

    # PostHog
    posthog_api_key: str = ""
    posthog_host: str = "https://us.posthog.com"
    posthog_enabled: bool = False

    # Health Checks
    health_check_interval_seconds: int = 300  # 5 minutes
    health_check_timeout_seconds: int = 10
    health_check_max_retries: int = 3

    # Rate Limiting
    rate_limit_submissions_per_hour: int = 10
    rate_limit_enabled: bool = True

    # Admin
    admin_api_key: str = ""

    # Logging
    log_json: bool = True
    log_level: str = "INFO"


settings = Settings()
