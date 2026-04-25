"""Typed application settings with explicit precedence.

Precedence is highest to lowest:
1. Process environment variables with the ``WAYWARDEN_`` prefix
2. ``.env`` in the current working directory
3. ``config/app.yaml`` values
4. ``AppConfig`` class defaults
"""

from pathlib import Path
from typing import Literal, Self, cast

import yaml

PolicyPresetLiteral = Literal["yolo", "ask", "allowlist", "custom"]

from fastapi import Request
from pydantic import SecretStr, ValidationInfo, field_validator, model_validator
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
    active_profile: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    env: str = "development"
    commit_sha: str = ""
    expose_commit_sha: bool = False
    database_url: str = ""
    tracer: Literal["noop", "otel"] = "noop"
    tracer_endpoint: str | None = None
    model_router: Literal["fake", "anthropic"] = "fake"
    model_router_default_provider: str = "fake"
    anthropic_api_key: SecretStr | None = None
    memory_provider: Literal["fake", "honcho"] = "fake"
    honcho_endpoint: str | None = None
    honcho_api_key: SecretStr | None = None
    knowledge_provider: Literal["filesystem", "llm_wiki"] = "filesystem"
    knowledge_filesystem_root: str = "assets/knowledge"
    llm_wiki_endpoint: str | None = None
    llm_wiki_api_key: SecretStr | None = None
    context_memory_char_cap: int = 2000
    context_knowledge_char_cap: int = 2000
    policy_preset: PolicyPresetLiteral = "ask"
    policy_overrides_path: Path | None = None
    active_instance: str | None = None
    instances_path: Path = Path("config/instances")
    web_channel_webhook_url: str | None = None
    resume_on_startup: bool = False

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

    @field_validator("active_profile", mode="before")
    @classmethod
    def normalize_active_profile(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("active_profile must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("active_profile must be set to a non-empty string")
        return normalized

    @field_validator("active_instance", mode="before")
    @classmethod
    def normalize_active_instance(cls, value: object | None) -> str | None:
        """Normalize ``active_instance`` and reject blank strings."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("active_instance must be a string or null")
        normalized = value.strip()
        if not normalized:
            raise ValueError("active_instance must be set to a non-empty string")
        return normalized

    @field_validator("tracer_endpoint")
    @classmethod
    def validate_tracer_endpoint(cls, value: str | None, info: ValidationInfo) -> str | None:
        tracer = info.data.get("tracer", "noop")
        if tracer == "otel" and not value:
            raise ValueError("tracer_endpoint must be set when tracer is 'otel'")
        return value

    @field_validator("model_router_default_provider", mode="before")
    @classmethod
    def normalize_model_router_default_provider(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("model_router_default_provider must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("model_router_default_provider must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_model_router(self) -> Self:
        if self.model_router == "anthropic" and self.anthropic_api_key is None:
            raise ValueError("anthropic_api_key must be set when model_router is 'anthropic'")
        policy_preset = self.policy_preset
        valid_presets = {"yolo", "ask", "allowlist", "custom"}
        if policy_preset not in valid_presets:
            raise ValueError(
                f"policy_preset must be one of {sorted(valid_presets)}, got '{policy_preset}'"
            )
        memory = self.memory_provider
        has_endpoint = self.honcho_endpoint is not None
        has_key = self.honcho_api_key is not None
        if memory == "honcho" and (not has_endpoint or not has_key):
            raise ValueError(
                "honcho_endpoint and honcho_api_key must be set when memory_provider is 'honcho'"
            )
        knowledge = self.knowledge_provider
        if knowledge == "llm_wiki":
            if not self.llm_wiki_endpoint:
                raise ValueError(
                    "llm_wiki_endpoint must be set when knowledge_provider is 'llm_wiki'"
                )
            if self.llm_wiki_api_key is None:
                raise ValueError(
                    "llm_wiki_api_key must be set when knowledge_provider is 'llm_wiki'"
                )
        active = self.active_instance
        instances = self.instances_path
        if active is not None:
            instance_yml = (instances / "instances.yaml").resolve()
            if not instance_yml.exists():
                raise ValueError(
                    f"instances_path {instances.as_posix()!r} does not contain "
                    f"instances.yaml required for active_instance={active!r}"
                )
            try:
                content = yaml.safe_load(instance_yml.read_text(encoding="utf-8"))
            except OSError as exc:
                raise ValueError(
                    f"{instance_yml.as_posix()}: unable to read instance YAML: {exc}"
                ) from exc
            if not isinstance(content, dict):
                raise ValueError(
                    f"{instance_yml.as_posix()}: expected a mapping of instance settings"
                )
            ids = {item["id"] for item in content.get("instances", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
            active_str: str = active
            if active_str not in ids:
                raise ValueError(
                    f"active_instance {active_str!r} does not match any loaded instance "
                    f"(available: {sorted(ids)})"
                )
        return self


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
