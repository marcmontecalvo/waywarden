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
