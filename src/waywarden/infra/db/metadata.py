"""Shared SQLAlchemy MetaData with naming convention for constraints.

Importing ``waywarden.infra.db.metadata`` registers all tables so that
``metadata.tables`` is fully populated for Alembic and for tests.
"""

from __future__ import annotations

from sqlalchemy import MetaData

naming_convention = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

# Import all table definitions to register them on the shared metadata.
# isort: off
from waywarden.infra.db.models import approval  # noqa: F401,E402
from waywarden.infra.db.models import checkpoint  # noqa: F401,E402
from waywarden.infra.db.models import message  # noqa: F401,E402
from waywarden.infra.db.models import run  # noqa: F401,E402
from waywarden.infra.db.models import run_event  # noqa: F401,E402
from waywarden.infra.db.models import session  # noqa: F401,E402
from waywarden.infra.db.models import task  # noqa: F401,E402
from waywarden.infra.db.models import token_usage  # noqa: F401,E402
from waywarden.infra.db.models import workspace_manifest  # noqa: F401,E402
