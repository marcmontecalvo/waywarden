from pathlib import Path

from sqlalchemy import MetaData

from waywarden.config.loader import ConfigLoadError, load_app_config
from waywarden.config.settings import DatabaseUrlMissing
from waywarden.infra.db.metadata import metadata as ALEMBIC_METADATA


def load_alembic_database_url(config_dir: Path | None = None, cwd: Path | None = None) -> str:
    try:
        app_config = load_app_config(config_dir=config_dir, cwd=cwd)
    except ConfigLoadError as exc:
        if _database_url_missing(exc):
            raise DatabaseUrlMissing(_DATABASE_URL_MISSING_MESSAGE) from exc
        raise

    if not app_config.database_url:
        raise DatabaseUrlMissing(_DATABASE_URL_MISSING_MESSAGE)

    return app_config.database_url


def _database_url_missing(exc: ConfigLoadError) -> bool:
    return any("field `database_url`" in error for error in exc.errors)


_DATABASE_URL_MISSING_MESSAGE = (
    "AppConfig.database_url is required for Alembic. "
    "Set WAYWARDEN_DATABASE_URL or add database_url to config/app.yaml."
)
