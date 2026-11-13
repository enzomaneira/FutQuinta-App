from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import (
    AttendanceStatus,
    GameStatus,
    PlayerType,
    Position,
    SlotType,
)


class AttendanceOut(BaseModel):
    player_id: int
    name: str
    position: Position
    player_type: PlayerType
    status: AttendanceStatus
    slot_type: SlotType
    late_cancellation: bool
    responded_at: datetime | None
    queued_at: datetime | None
    queue_position: int | None = None  # 1 = próximo a ser chamado
    referred_by_name: str | None = None  # mensalista que trouxe o avulso


class SlotOut(BaseModel):
    capacity: int
    confirmed: int
    pending: int
    free: int


class BibPlayerOut(BaseModel):
    id: int
    name: str


class GameSummary(BaseModel):
    id: int
    status: GameStatus
    local_date: date
    start_time: str  # "21:30" (horário local)
    end_time: str
    starts_at: datetime
    occupied: int  # confirmados + pendentes
    capacity: int


class GameDetail(GameSummary):
    ends_at: datetime
    confirmation_deadline: datetime
    late_cancellation_at: datetime
    deadline_passed: bool
    editable: bool
    bib_player: BibPlayerOut | None
    slots: dict[Position, SlotOut]
    alerts: list[str]
    lineup: dict[Position, list[AttendanceOut]]  # quem ocupa vaga
    queue: dict[Position, list[AttendanceOut]]  # fila de avulsos
    out: list[AttendanceOut]  # desmarcou / perdeu a vaga


class CalendarOut(BaseModel):
    month: str  # "2026-11"
    game_weekday: int  # 0 = segunda ... 6 = domingo
    due_day: int  # dia de vencimento da mensalidade
    games: list[GameSummary]


class CreateGameIn(BaseModel):
    date: date


class SubstituteIn(BaseModel):
    out_player_id: int
    in_player_id: int


class PresenceIn(BaseModel):
    present: bool


class BibIn(BaseModel):
    player_id: int | None


class QueueIn(BaseModel):
    player_id: int


class CallNextIn(BaseModel):
    position: Position
