from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import UserRole, db_enum
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    """Organizador com acesso ao app."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        db_enum(UserRole), default=UserRole.ORGANIZER
    )
    active: Mapped[bool] = mapped_column(default=True)
