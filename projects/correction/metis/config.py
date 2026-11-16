"""Centralized environment configuration and startup validation."""

from decimal import Decimal
from typing import Annotated

from pydantic import AliasChoices, Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from projects.correction.agents.schemas.evaluation import EvaluationMode
from projects.correction.agents.specs import ModelSpec, Role, development_spec, validate_catalog


class MetisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="METIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
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
    evaluation_method: str = Field(default="standard", min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    evaluation_mode: EvaluationMode = EvaluationMode.SECTIONED
    profiling_taxonomy_version: str = ""

    # Opcional: amplia a cota de leitura da taxonomia pública do OpenAlex.
    openalex_api_key: str = ""
    crossref_mailto: str = ""
    semantic_scholar_api_key: str = ""
    unpaywall_email: str = ""
    profiling_max_attempts: int = Field(default=3, ge=1)
    profiling_confidence_threshold: float = Field(default=0.7, ge=0, le=1, allow_inf_nan=False)
    max_revision_rounds: int = Field(default=2, ge=1)

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
    openai_api_key: str = ""
    google_api_key: str = Field(
        default="", validation_alias=AliasChoices("METIS_GOOGLE_API_KEY", "GEMINI_KEY")
    )
    llm_max_concurrency: int = Field(default=4, ge=1)
    # Limite de alerta no admin, em USD por run; ausente desativa a comparação.
    llm_run_budget_usd: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    evaluator_a: ModelSpec = Field(default_factory=lambda: development_spec(Role.EVALUATOR_A))
    evaluator_b: ModelSpec = Field(default_factory=lambda: development_spec(Role.EVALUATOR_B))
    evaluator_c: ModelSpec = Field(default_factory=lambda: development_spec(Role.EVALUATOR_C))
    judge_openai: ModelSpec = Field(default_factory=lambda: development_spec(Role.JUDGE_OPENAI))
    judge_google: ModelSpec = Field(default_factory=lambda: development_spec(Role.JUDGE_GOOGLE))
    meta_reviewer: ModelSpec = Field(default_factory=lambda: development_spec(Role.META_REVIEWER))
    vision: ModelSpec = Field(default_factory=lambda: development_spec(Role.VISION))
    fast: ModelSpec = Field(default_factory=lambda: development_spec(Role.FAST))
    adjudicator: ModelSpec = Field(default_factory=lambda: development_spec(Role.ADJUDICATOR))
    # Modelos mínimos para os contratos ao vivo; não definem os papéis da etapa 1.3.
    agno_contract_openai_model: str = "gpt-4o-mini"
    agno_contract_google_model: str = "gemini-3.6-flash"

    @property
    def model_specs(self) -> dict[Role, ModelSpec]:
        return {role: getattr(self, role.value) for role in Role}

    @field_validator(*(role.value for role in Role), mode="before")
    @classmethod
    def model_override(cls, value: object, info: ValidationInfo) -> object:
        if isinstance(value, dict):
            assert info.field_name is not None
            defaults = development_spec(Role(info.field_name)).model_dump()
            return defaults | value
        return value

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
        validate_catalog(self.model_specs)
        for role, spec in self.model_specs.items():
            if spec.timeout_seconds >= self.stage_soft_time_limit_seconds:
                raise ValueError(f"O timeout de {role} deve ser menor que o limite soft.")
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
