from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from waywarden.config import ALEMBIC_METADATA, load_alembic_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = ALEMBIC_METADATA


def run_migrations_offline() -> None:
    url = load_alembic_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = load_alembic_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        if _is_current_command() and not context.get_context().get_current_heads():
            config.print_stdout("(none)")

        with context.begin_transaction():
            context.run_migrations()


def _is_current_command() -> bool:
    cmd = getattr(getattr(config, "cmd_opts", None), "cmd", None)
    if not isinstance(cmd, tuple) or not cmd:
        return False
    command_fn = cmd[0]
    return callable(command_fn) and getattr(command_fn, "__name__", "") == "current"


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
