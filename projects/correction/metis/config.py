"""Centralized environment configuration and startup validation."""

from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class MetisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="METIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = "development-only-change-before-deploying"
    debug: bool = False
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"]
    )
    csrf_trusted_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    postgres_host: str = "localhost"
    postgres_port: int = 5440
    postgres_db: str = "metis"
    postgres_user: str = "metis"
    postgres_password: str = "metis"
    redis_url: str = "redis://localhost:6379/0"
    api_token: str = ""
    media_root: str = "media"
    max_upload_mb: int = 50

    stage_max_retries: int = 3
    stage_retry_backoff_seconds: int = 60
    stage_retry_backoff_max_seconds: int = 900
    stage_soft_time_limit_seconds: int = 1500
    stage_time_limit_seconds: int = 1800
    broker_visibility_timeout_seconds: int = 7200
    reconcile_interval_seconds: int = 300
    republish_after_seconds: int = 900
    stale_stage_after_seconds: int = 2700
    max_republish: int = 3
    max_stage_claims: int = 8

    # Chave da API do Gemini, lida do .env sem o prefixo METIS_.
    gemini_key: str = Field(default="", validation_alias="GEMINI_KEY")
    llm_timeout_seconds: int = 600

    @field_validator("allowed_hosts", "csrf_trusted_origins", mode="before")
    @classmethod
    def split_csv_values(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "stage_max_retries",
        "stage_retry_backoff_seconds",
        "stage_retry_backoff_max_seconds",
        "stage_soft_time_limit_seconds",
        "stage_time_limit_seconds",
        "broker_visibility_timeout_seconds",
        "reconcile_interval_seconds",
        "republish_after_seconds",
        "stale_stage_after_seconds",
        "max_republish",
        "max_stage_claims",
        "llm_timeout_seconds",
    )
    @classmethod
    def values_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("O valor deve ser maior que zero.")
        return value

    @model_validator(mode="after")
    def validate_task_timing(self) -> MetisSettings:
        if not self.stage_soft_time_limit_seconds < self.stage_time_limit_seconds:
            raise ValueError("O limite soft deve ser menor que o limite hard da task.")
        if not self.stage_time_limit_seconds < self.broker_visibility_timeout_seconds:
            raise ValueError("O limite hard deve ser menor que o visibility timeout do broker.")
        if not self.stage_retry_backoff_max_seconds < self.broker_visibility_timeout_seconds:
            raise ValueError("O teto do backoff deve ser menor que o visibility timeout do broker.")
        if not self.stale_stage_after_seconds > self.stage_time_limit_seconds:
            raise ValueError("O prazo de estágio travado deve exceder o limite hard da task.")
        if not self.max_stage_claims > self.stage_max_retries + 1:
            raise ValueError("O máximo de claims deve exceder retries + 1.")
        if not self.llm_timeout_seconds < self.stage_soft_time_limit_seconds:
            raise ValueError("O timeout da chamada ao modelo deve ser menor que o limite soft.")
        return self


settings = MetisSettings()
