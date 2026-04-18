from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from waywarden.config.settings import AppConfig


class ConfigLoadError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Configuration loading failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def load_app_config(config_dir: Path | None = None, cwd: Path | None = None) -> AppConfig:
    resolved_config_dir = (config_dir or Path("config")).resolve()
    resolved_cwd = (cwd or Path.cwd()).resolve()
    yaml_errors, app_yaml_is_valid = _collect_yaml_errors(resolved_config_dir)
    errors = list(yaml_errors)

    app_config_path = resolved_config_dir / "app.yaml"
    if app_yaml_is_valid:
        AppConfig.yaml_file = app_config_path

        try:
            return AppConfig(_env_file=resolved_cwd / ".env")  # type: ignore[call-arg]
        except ValidationError as exc:
            errors.extend(_format_validation_errors(app_config_path, exc))
        finally:
            AppConfig.yaml_file = None

    if errors:
        raise ConfigLoadError(errors)

    raise ConfigLoadError(
        [f"{app_config_path.as_posix()}: no application settings could be loaded"]
    )


@lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    return load_app_config()


def clear_app_config_cache() -> None:
    get_app_config.cache_clear()


def _collect_yaml_errors(config_dir: Path) -> tuple[list[str], bool]:
    errors: list[str] = []
    app_yaml_is_valid = True
    for yaml_path in sorted(config_dir.glob("*.yaml")):
        try:
            content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            reason = getattr(exc, "problem", None) or str(exc)
            errors.append(f"{yaml_path.as_posix()}: YAML parse error: {reason}")
            if yaml_path.name == "app.yaml":
                app_yaml_is_valid = False
            continue

        if yaml_path.name == "app.yaml" and content is not None and not isinstance(content, dict):
            errors.append(f"{yaml_path.as_posix()}: expected a mapping of app settings")
            app_yaml_is_valid = False
    return errors, app_yaml_is_valid


def _format_validation_errors(app_config_path: Path, exc: ValidationError) -> list[str]:
    errors: list[str] = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        reason = error["msg"]
        errors.append(
            f"{app_config_path.as_posix()}: field `{field}`: {reason} "
            "(after env > .env > yaml precedence)"
        )
    return errors
