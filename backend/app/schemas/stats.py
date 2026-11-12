from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import (
    AttendanceStatus,
    ChargeType,
    GameStatus,
    PaymentMethod,
)
from app.schemas.finance import CashOut, ChargeOut
from app.schemas.games import GameDetail


class StatsOut(BaseModel):
    games_played: int
    cancellations: int
    late_cancellations: int
    no_shows: int
    no_response: int
    bib_times: int
    attendance_base: int
    attendance_rate: float | None


class RecentGameOut(BaseModel):
    game_id: int
    local_date: date
    game_status: GameStatus
    status: AttendanceStatus
    late_cancellation: bool


class PaymentOut(BaseModel):
    charge_id: int
    charge_type: ChargeType
    reference: str
    amount_cents: int
    paid_at: datetime
    method: PaymentMethod


class ProfileOut(BaseModel):
    stats: StatsOut
    open_charges: list[ChargeOut]
    payments: list[PaymentOut]
    recent_games: list[RecentGameOut]


class VenueOut(BaseModel):
    name: str
    address: str
    lat: float
    lng: float


class OpenChargesSummary(BaseModel):
    count: int
    overdue: int
    total_cents: int
    items: list[ChargeOut]  # os primeiros, mais antigos primeiro


class HomeOut(BaseModel):
    game: GameDetail | None
    cash: CashOut
    venue: VenueOut
    open_charges: OpenChargesSummary
    pix_key: str


class GameChargesOut(BaseModel):
    """Valores do jogo no Histórico: cobranças dos avulsos daquele jogo."""

    charges: list[ChargeOut]
    received_cents: int
    expected_cents: int
