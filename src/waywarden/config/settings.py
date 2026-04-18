"""Typed application settings with explicit precedence.

Precedence is highest to lowest:
1. Process environment variables with the ``WAYWARDEN_`` prefix
2. ``.env`` in the current working directory
3. ``config/app.yaml`` values
4. ``AppConfig`` class defaults
"""

from pathlib import Path
from typing import ClassVar, Literal, cast

from fastapi import Request
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class AppConfig(BaseSettings):
    host: str
    port: int
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    env: str = "development"
    commit_sha: str = ""
    expose_commit_sha: bool = False

    model_config = SettingsConfigDict(
        env_prefix="WAYWARDEN_",
        env_file=".env",
        extra="ignore",
        validate_default=True,
    )

    yaml_file: ClassVar[Path | None] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_source = YamlConfigSettingsSource(settings_cls, yaml_file=cls.yaml_file)
        return init_settings, env_settings, dotenv_settings, yaml_source, file_secret_settings


def get_request_app_config(request: Request) -> AppConfig:
    return cast(AppConfig, request.app.state.settings)
