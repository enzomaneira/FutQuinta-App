from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class JobRun(Base):
    """Registro das rotinas periódicas já executadas (ex.: mensalidades de
    "2026-11"). O único (name, period) garante que cada uma roda uma vez por
    período, mesmo com o servidor reiniciando — e serve de log."""

    __tablename__ = "job_runs"
    __table_args__ = (UniqueConstraint("name", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    period: Mapped[str] = mapped_column(String(20))
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    details: Mapped[Any] = mapped_column(JSONB, default=dict)
