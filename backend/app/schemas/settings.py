"""Validação da tela de Configurações. Todos os campos são opcionais no
PATCH: só o que for enviado é gravado."""

import re

from pydantic import BaseModel, Field, field_validator

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class SettingsUpdate(BaseModel):
    # Local
    venue_name: str | None = Field(default=None, min_length=1, max_length=100)
    venue_address: str | None = Field(default=None, min_length=1, max_length=200)
    venue_lat: float | None = Field(default=None, ge=-90, le=90)
    venue_lng: float | None = Field(default=None, ge=-180, le=180)
    # Jogo
    game_weekday: int | None = Field(default=None, ge=0, le=6)
    game_start_time: str | None = None
    game_end_time: str | None = None
    goalkeeper_slots: int | None = Field(default=None, ge=0, le=10)
    field_slots: int | None = Field(default=None, ge=1, le=40)
    # Lista
    list_open_days_before: int | None = Field(default=None, ge=0, le=6)
    list_open_time: str | None = None
    confirmation_deadline_time: str | None = None
    late_cancellation_time: str | None = None
    # Valores (centavos)
    monthly_fee_cents: int | None = Field(default=None, ge=0)
    drop_in_fee_cents: int | None = Field(default=None, ge=0)
    court_monthly_cents: int | None = Field(default=None, ge=0)
    initial_cash_cents: int | None = None  # pode ser negativo
    # Cobrança
    billing_day: int | None = Field(default=None, ge=1, le=28)
    monthly_due_day: int | None = Field(default=None, ge=1, le=28)
    # Pix
    pix_key: str | None = Field(default=None, max_length=120)

    @field_validator(
        "game_start_time",
        "game_end_time",
        "list_open_time",
        "confirmation_deadline_time",
        "late_cancellation_time",
    )
    @classmethod
    def check_time(cls, value: str | None) -> str | None:
        if value is not None and not HHMM.match(value):
            raise ValueError("Use o formato HH:MM (ex.: 21:30)")
        return value
