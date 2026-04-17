from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from waywarden.adapters.db.base import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
