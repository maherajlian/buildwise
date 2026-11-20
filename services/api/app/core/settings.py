from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://buildwise:buildwise@localhost:5432/buildwise"
    )
    cors_origins: list[str] = ["http://localhost:3000"]
    otel_service_name: str = "buildwise-api"
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""
    otel_traces_sampler: Literal["parentbased_traceidratio"] = (
        "parentbased_traceidratio"
    )
    otel_traces_sampler_arg: float = Field(default=0.1, ge=0, le=1)

    @field_validator("cors_origins")
    @classmethod
    def restricted_origins(cls, value: list[str]) -> list[str]:
        if any(
            origin == "*" or not origin.startswith(("http://", "https://"))
            for origin in value
        ):
            raise ValueError("CORS requires explicit HTTP origins")
        return value


def database_url(value: str) -> str:
    if value.startswith(("postgres://", "postgresql://")):
        return "postgresql+psycopg://" + value.split("://", 1)[1]
    return value
