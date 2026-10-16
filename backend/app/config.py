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
    database_statement_timeout_ms: int = 10000  # 10s max per query

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "https://a2aregistry.org", "https://www.a2aregistry.org"]

    # PostHog
    posthog_api_key: str = ""
    posthog_host: str = "https://us.posthog.com"
    posthog_enabled: bool = False

    # Health Checks
    health_check_interval_seconds: int = 300  # 5 minutes
    health_check_timeout_seconds: int = 10
    health_check_max_retries: int = 3

    # Rate Limiting
    rate_limit_enabled: bool = True

    # Admin
    admin_api_key: str = ""

    # Jev (TypeSafe) Agent Card classifier. Pin the model: the threshold was
    # tuned against this version. A missing key fails closed.
    jev_api_key: str = ""
    jev_model: str = "jev-1.13.0"
    jev_threshold: float = 0.45
    jev_timeout_seconds: float = 20.0  # per Jev request
    jev_deadline_seconds: float = 45.0  # whole card at registration/PUT, including queueing
    # Service-wide registration attempts that reach a card fetch, both register
    # endpoints together. Sized from Sep-Oct 2026: about 8 registrations a day,
    # a busiest legitimate day of 26 (17 in one hour); a 101-a-day burst (80 in
    # one hour) is what this stops. See rate_limits.registration_limits.
    registration_daily_limit: int = 60
    registration_hourly_limit: int = 25

    # Hard ceilings on Jev requests (one per card window, about 6.2k input
    # tokens each). Sized from October 2026 usage: the worker re-scores about 60
    # changed cards a day at about 7.4 requests each (about 450 requests), new
    # registrations add about 40; the busiest day was about 1.7k. The daily
    # ceiling is split: submissions get jev_submission_daily_requests, the worker
    # and admin get the rest, and a re-score wave spills into later days.
    # See rate_limits.py.
    jev_daily_requests: int = 1200
    jev_submission_daily_requests: int = 200
    jev_submission_hourly_requests: int = 60
    jev_client_daily_requests: int = 60

    # Logging
    log_json: bool = True
    log_level: str = "INFO"


settings = Settings()
