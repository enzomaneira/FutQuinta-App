"""Enums do domínio.

No banco viram VARCHAR (native_enum=False): adicionar um valor novo na Fase 2
(ex.: origem "whatsapp" de pagamento) não exige ALTER TYPE no Postgres.
"""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def db_enum(enum_cls: type[StrEnum]) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class UserRole(StrEnum):
    ADMIN = "admin"
    ORGANIZER = "organizer"


class PlayerType(StrEnum):
    MONTHLY = "monthly"  # mensalista
    DROP_IN = "drop_in"  # avulso


class Position(StrEnum):
    GOALKEEPER = "goalkeeper"
    FIELD = "field"  # linha


class GameStatus(StrEnum):
    DRAFT = "draft"  # rascunho
    OPEN = "open"  # lista aberta
    CLOSED = "closed"  # lista fechada
    PLAYED = "played"  # realizado
    CANCELLED = "cancelled"


class AttendanceStatus(StrEnum):
    PENDING = "pending"  # mensalista ainda não respondeu
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"  # desmarcou
    RELEASED = "released"  # perdeu a vaga garantida no prazo (liberado)
    QUEUED = "queued"  # avulso na fila de espera
    ABSENT = "absent"  # faltou (após o jogo)
    PRESENT = "present"  # compareceu (após o jogo)


class SlotType(StrEnum):
    MONTHLY = "monthly"
    DROP_IN = "drop_in"


class AttendanceSource(StrEnum):
    APP = "app"
    BOT = "bot"


class ChargeType(StrEnum):
    MONTHLY_FEE = "monthly_fee"
    DROP_IN = "drop_in"


class ChargeStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"  # atrasado
    WAIVED = "waived"  # isento


class PaymentMethod(StrEnum):
    PIX = "pix"
    CASH = "cash"


class PaymentSource(StrEnum):
    MANUAL = "manual"


class ExpenseCategory(StrEnum):
    COURT = "court"  # quadra
    BIBS = "bibs"  # coletes
    BALL = "ball"
    OTHER = "other"


class ExpenseType(StrEnum):
    FIXED = "fixed"
    VARIABLE = "variable"
