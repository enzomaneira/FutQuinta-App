"""Ciclo de vida do jogo: criação, abertura da lista, liberação de vagas,
fechamento, cancelamento e coletes.

As transições por horário (`run_due_transitions`) são idempotentes e se
baseiam só no que está no banco. A rotina agendada chama a cada minuto; se o
servidor ficou fora do ar, ela recupera o atraso na primeira execução.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.models.attendance import Attendance
from app.models.enums import (
    AttendanceStatus as S,
    GameStatus,
    PlayerType,
    SlotType,
)
from app.models.game import Game
from app.models.player import Player
from app.services import billing
from app.services.attendance import get_game
from app.services.errors import ConflictError, DomainError, NotFoundError
from app.services.schedule import game_times, local_day_bounds, next_game_day
from app.services.settings import get_all_settings

logger = logging.getLogger(__name__)

ACTIVE = (GameStatus.DRAFT, GameStatus.OPEN, GameStatus.CLOSED)


def find_game_on(db: Session, day: date) -> Game | None:
    start, end = local_day_bounds(day)
    return db.scalar(
        select(Game).where(Game.starts_at >= start, Game.starts_at < end).limit(1)
    )


def list_games(db: Session, first_day: date, last_day: date) -> list[Game]:
    start, _ = local_day_bounds(first_day)
    _, end = local_day_bounds(last_day)
    return list(
        db.scalars(
            select(Game)
            .where(Game.starts_at >= start, Game.starts_at < end)
            .order_by(Game.starts_at)
        )
    )


def current_game(db: Session, now: datetime | None = None) -> Game | None:
    """O jogo "da semana": o próximo que ainda não terminou (com folga de 6h
    depois do fim, para ajustar presenças na mesma noite); senão o último."""
    now = now or now_utc()
    upcoming = db.scalar(
        select(Game)
        .where(Game.ends_at >= now - timedelta(hours=6))
        .order_by(Game.starts_at)
        .limit(1)
    )
    if upcoming is not None:
        return upcoming
    return db.scalar(select(Game).order_by(Game.starts_at.desc()).limit(1))


def create_game(db: Session, day: date, *, now: datetime | None = None) -> Game:
    """Cria o jogo do dia com a lista aberta e todos os mensalistas ativos
    como pendentes."""
    if find_game_on(db, day) is not None:
        raise ConflictError("Já existe um jogo neste dia")
    game = _create_game(db, day)
    db.commit()
    db.refresh(game)
    return game


def _create_game(db: Session, day: date) -> Game:
    values = get_all_settings(db)
    times = game_times(db, day, values)
    game = Game(
        starts_at=times.starts_at,
        ends_at=times.ends_at,
        confirmation_deadline=times.confirmation_deadline,
        status=GameStatus.OPEN,
        goalkeeper_slots=int(values["goalkeeper_slots"]),
        field_slots=int(values["field_slots"]),
    )
    db.add(game)
    db.flush()
    monthly = db.scalars(
        select(Player).where(Player.type == PlayerType.MONTHLY, Player.active.is_(True))
    )
    for player in monthly:
        db.add(
            Attendance(
                game_id=game.id,
                player_id=player.id,
                status=S.PENDING,
                slot_type=SlotType.MONTHLY,
            )
        )
    return game


# --- transições por horário (rotina agendada) ---


@dataclass
class TransitionResult:
    opened_game_id: int | None = None
    released: int = 0  # mensalistas pendentes que perderam a vaga garantida
    closed_games: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.opened_game_id or self.released or self.closed_games)


def run_due_transitions(db: Session, now: datetime | None = None) -> TransitionResult:
    now = now or now_utc()
    result = TransitionResult()
    result.opened_game_id = _open_upcoming_list(db, now)
    result.released = _release_pending(db, now)
    result.closed_games = _close_finished_games(db, now)
    db.commit()
    if result.changed:
        logger.info(
            "Rotina do jogo: aberto=%s liberados=%d encerrados=%d",
            result.opened_game_id,
            result.released,
            result.closed_games,
        )
    return result


def _open_upcoming_list(db: Session, now: datetime) -> int | None:
    """Terça 10h (padrão): cria o jogo de quinta e abre a lista.

    Só abre sozinho até o prazo de confirmação: depois disso os mensalistas
    já perderiam a vaga na hora (ex.: servidor ligado na quinta à tarde).
    Nesse caso o organizador cria o jogo pelo Calendário, se quiser.
    """
    values = get_all_settings(db)
    day = next_game_day(db, now, values)
    times = game_times(db, day, values)
    if not (times.list_opens_at <= now < times.confirmation_deadline):
        return None
    if find_game_on(db, day) is not None:
        return None  # já criado (ou cancelado pelo organizador)
    return _create_game(db, day).id


def _release_pending(db: Session, now: datetime) -> int:
    """Quinta 12h (padrão): pendentes perdem a vaga garantida."""
    due_games = select(Game.id).where(
        Game.status.in_(ACTIVE), Game.confirmation_deadline <= now
    )
    result = db.execute(
        update(Attendance)
        .where(Attendance.game_id.in_(due_games), Attendance.status == S.PENDING)
        .values(status=S.RELEASED)
    )
    return result.rowcount or 0


def _close_finished_games(db: Session, now: datetime) -> int:
    """Depois do fim do jogo: confirmados viram "compareceu" e o jogo vira
    "realizado". O organizador corrige as faltas depois."""
    games = list(
        db.scalars(select(Game).where(Game.status.in_(ACTIVE), Game.ends_at <= now))
    )
    for game in games:
        db.execute(
            update(Attendance)
            .where(Attendance.game_id == game.id, Attendance.status == S.CONFIRMED)
            .values(status=S.PRESENT)
        )
        db.execute(
            update(Attendance)
            .where(Attendance.game_id == game.id, Attendance.status == S.PENDING)
            .values(status=S.RELEASED)
        )
        game.status = GameStatus.PLAYED
    return len(games)


# --- ações do organizador ---


def close_list(db: Session, game_id: int) -> Game:
    game = get_game(db, game_id, lock=True)
    if game.status not in (GameStatus.DRAFT, GameStatus.OPEN):
        raise DomainError("Só dá para fechar uma lista aberta")
    game.status = GameStatus.CLOSED
    db.commit()
    return game


def reopen_list(db: Session, game_id: int) -> Game:
    """Reabre uma lista fechada ou um jogo cancelado por engano."""
    game = get_game(db, game_id, lock=True)
    if game.status not in (GameStatus.CLOSED, GameStatus.CANCELLED):
        raise DomainError("Só dá para reabrir uma lista fechada ou um jogo cancelado")
    if game.status == GameStatus.CANCELLED:
        # Avulsos confirmados voltam a ser cobrados
        for attendance in _confirmed_drop_ins(db, game.id):
            billing.ensure_drop_in_charge(db, attendance.player_id, game)
    game.status = GameStatus.OPEN
    db.commit()
    return game


def cancel_game(db: Session, game_id: int) -> Game:
    """Cancela o jogo (chuva, feriado...). Avulsos confirmados ficam isentos."""
    game = get_game(db, game_id, lock=True)
    if game.status == GameStatus.PLAYED:
        raise DomainError("Este jogo já foi realizado")
    for attendance in _confirmed_drop_ins(db, game.id):
        billing.waive_drop_in_charge(db, attendance.player_id, game)
    game.status = GameStatus.CANCELLED
    db.commit()
    return game


def set_bib_player(db: Session, game_id: int, player_id: int | None) -> Game:
    """Define quem leva os coletes (escolha manual do organizador)."""
    game = get_game(db, game_id, lock=True)
    if player_id is not None and db.get(Player, player_id) is None:
        raise NotFoundError("Jogador não encontrado")
    game.bib_player_id = player_id
    db.commit()
    return game


def _confirmed_drop_ins(db: Session, game_id: int) -> list[Attendance]:
    return list(
        db.scalars(
            select(Attendance).where(
                Attendance.game_id == game_id,
                Attendance.slot_type == SlotType.DROP_IN,
                Attendance.status.in_((S.CONFIRMED, S.PRESENT)),
            )
        )
    )
