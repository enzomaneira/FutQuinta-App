"""Estatísticas do perfil do jogador.

Tudo é calculado na hora a partir de presenças, jogos, cobranças e
pagamentos — não existem contadores duplicados para manter em sincronia.
Jogos cancelados não contam.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.charge import Charge
from app.models.enums import AttendanceStatus as S, GameStatus
from app.models.game import Game
from app.models.payment import Payment


@dataclass
class PlayerStats:
    games_played: int = 0  # compareceu
    cancellations: int = 0  # desmarcou (qualquer horário)
    late_cancellations: int = 0  # desmarcou em cima da hora
    no_shows: int = 0  # faltou sem avisar (estava confirmado)
    no_response: int = 0  # mensalista que não respondeu até o prazo
    bib_times: int = 0  # vezes com os coletes
    # Presença = compareceu / jogos realizados em que estava na lista
    attendance_base: int = 0
    attendance_rate: float | None = None


@dataclass
class RecentGame:
    game_id: int
    starts_at: datetime
    game_status: GameStatus
    status: S
    late_cancellation: bool


@dataclass
class PlayerProfile:
    stats: PlayerStats
    recent: list[RecentGame] = field(default_factory=list)
    payments: list[tuple[Payment, Charge]] = field(default_factory=list)


def player_stats(db: Session, player_id: int) -> PlayerStats:
    rows = db.execute(
        select(Attendance, Game)
        .join(Game, Game.id == Attendance.game_id)
        .where(Attendance.player_id == player_id, Game.status != GameStatus.CANCELLED)
    ).tuples()

    stats = PlayerStats()
    for attendance, game in rows:
        status = attendance.status
        if status == S.PRESENT:
            stats.games_played += 1
        elif status == S.ABSENT:
            stats.no_shows += 1
        elif status == S.CANCELLED:
            stats.cancellations += 1
            stats.late_cancellations += int(attendance.late_cancellation)
        elif status == S.RELEASED:
            stats.no_response += 1
        # Base da presença: jogos já realizados em que ele estava na lista
        # (fila não conta: avulso na fila não tinha vaga)
        if game.status == GameStatus.PLAYED and status != S.QUEUED:
            stats.attendance_base += 1

    if stats.attendance_base:
        stats.attendance_rate = stats.games_played / stats.attendance_base

    stats.bib_times = db.scalar(
        select(func.count())
        .select_from(Game)
        .where(Game.bib_player_id == player_id, Game.status != GameStatus.CANCELLED)
    ) or 0
    return stats


def player_profile(db: Session, player_id: int, *, recent_limit: int = 10) -> PlayerProfile:
    recent = [
        RecentGame(
            game_id=game.id,
            starts_at=game.starts_at,
            game_status=game.status,
            status=attendance.status,
            late_cancellation=attendance.late_cancellation,
        )
        for attendance, game in db.execute(
            select(Attendance, Game)
            .join(Game, Game.id == Attendance.game_id)
            .where(Attendance.player_id == player_id)
            .order_by(Game.starts_at.desc())
            .limit(recent_limit)
        ).tuples()
    ]
    payments = list(
        db.execute(
            select(Payment, Charge)
            .join(Charge, Charge.id == Payment.charge_id)
            .where(Charge.player_id == player_id)
            .order_by(Payment.paid_at.desc())
            .limit(24)
        ).tuples()
    )
    return PlayerProfile(stats=player_stats(db, player_id), recent=recent, payments=payments)
