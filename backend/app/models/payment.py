from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import PaymentMethod, PaymentSource, db_enum
from app.models.mixins import TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    charge_id: Mapped[int] = mapped_column(
        ForeignKey("charges.id", ondelete="RESTRICT"), index=True
    )
    amount_cents: Mapped[int]
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    method: Mapped[PaymentMethod] = mapped_column(db_enum(PaymentMethod))
    source: Mapped[PaymentSource] = mapped_column(
        db_enum(PaymentSource), default=PaymentSource.MANUAL
    )
    receipt_url: Mapped[str | None] = mapped_column(String(500))  # Fase 2
