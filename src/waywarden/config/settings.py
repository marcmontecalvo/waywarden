"""Typed application settings with explicit precedence.

Precedence is highest to lowest:
1. Process environment variables with the ``WAYWARDEN_`` prefix
2. ``.env`` in the current working directory
3. ``config/app.yaml`` values
4. ``AppConfig`` class defaults
"""

from pathlib import Path
from typing import Literal, cast

from fastapi import Request
from pydantic import ValidationInfo, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class DatabaseUrlMissing(RuntimeError):
    """Raised when migration tooling cannot resolve a database URL."""


class AppConfig(BaseSettings):
    host: str
    port: int
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    env: str = "development"
    commit_sha: str = ""
    expose_commit_sha: bool = False
    database_url: str = ""
    tracer: Literal["noop", "otel"] = "noop"
    tracer_endpoint: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="WAYWARDEN_",
        env_file=".env",
        extra="ignore",
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        raise TypeError("database_url must be a string")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str, info: ValidationInfo) -> str:
        env = info.data.get("env", "development")
        if env in {"production", "test"} and not value:
            raise ValueError("must be set to a non-empty string when env is 'production' or 'test'")
        return value

    @field_validator("tracer_endpoint")
    @classmethod
    def validate_tracer_endpoint(cls, value: str | None, info: ValidationInfo) -> str | None:
        tracer = info.data.get("tracer", "noop")
        if tracer == "otel" and not value:
            raise ValueError("tracer_endpoint must be set when tracer is 'otel'")
        return value


def build_app_config_class(yaml_file: Path | None) -> type[AppConfig]:
    """Create an AppConfig subclass with a per-load YAML source.

    The base AppConfig class stays immutable so repeated or concurrent loads do not
    mutate shared class state.
    """

    class LoadedAppConfig(AppConfig):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            sources: list[PydanticBaseSettingsSource] = [
                init_settings,
                env_settings,
                dotenv_settings,
            ]
            if yaml_file is not None:
                sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file))
            sources.append(file_secret_settings)
            return tuple(sources)

    return LoadedAppConfig


def get_request_app_config(request: Request) -> AppConfig:
    return cast(AppConfig, request.app.state.settings)
