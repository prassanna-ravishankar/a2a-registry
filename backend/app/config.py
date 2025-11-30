"""Configuration management using pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://localhost/a2a_registry"
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
    posthog_enabled: bool = True

    # Health Checks
    health_check_interval_seconds: int = 300  # 5 minutes
    health_check_timeout_seconds: int = 10
    health_check_max_retries: int = 3

    # Rate Limiting
    rate_limit_submissions_per_hour: int = 10
    rate_limit_enabled: bool = True


settings = Settings()
