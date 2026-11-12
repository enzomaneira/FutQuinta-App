"""Cálculo de datas e horários do jogo a partir das Configurações.

Tudo que o organizador vê (terça 10h, quinta 12h, quinta 18h...) é horário
local (America/Sao_Paulo); no banco guardamos UTC.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.clock import local_tz
from app.services.settings import get_all_settings


def parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def local_to_utc(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=local_tz()).astimezone(UTC)


def local_date_of(moment: datetime) -> date:
    return moment.astimezone(local_tz()).date()


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    """Início e fim (UTC) de um dia local, para buscar jogos por data."""
    start = datetime.combine(day, time(0, 0), tzinfo=local_tz())
    end = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=local_tz())
    return start.astimezone(UTC), end.astimezone(UTC)


@dataclass(frozen=True)
class GameTimes:
    starts_at: datetime
    ends_at: datetime
    confirmation_deadline: datetime  # pendentes perdem a vaga garantida
    late_cancellation_at: datetime  # desmarcar depois disso = em cima da hora
    list_opens_at: datetime


def game_times(db: Session, game_day: date, values: dict | None = None) -> GameTimes:
    s = values or get_all_settings(db)
    start = parse_hhmm(s["game_start_time"])
    end = parse_hhmm(s["game_end_time"])
    end_day = game_day + timedelta(days=1) if end <= start else game_day  # passa da meia-noite
    open_day = game_day - timedelta(days=int(s["list_open_days_before"]))
    return GameTimes(
        starts_at=local_to_utc(game_day, start),
        ends_at=local_to_utc(end_day, end),
        confirmation_deadline=local_to_utc(
            game_day, parse_hhmm(s["confirmation_deadline_time"])
        ),
        late_cancellation_at=local_to_utc(
            game_day, parse_hhmm(s["late_cancellation_time"])
        ),
        list_opens_at=local_to_utc(open_day, parse_hhmm(s["list_open_time"])),
    )


def late_cancellation_at(db: Session, starts_at: datetime) -> datetime:
    """Limite de "em cima da hora" para um jogo já criado (no dia do jogo)."""
    return game_times(db, local_date_of(starts_at)).late_cancellation_at


def next_game_day(db: Session, now: datetime, values: dict | None = None) -> date:
    """Próximo dia de jogo (hoje conta, se for o dia)."""
    s = values or get_all_settings(db)
    today = local_date_of(now)
    ahead = (int(s["game_weekday"]) - today.weekday()) % 7
    return today + timedelta(days=ahead)
