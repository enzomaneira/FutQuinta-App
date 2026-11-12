"""Fila de avulsos de um jogo.

A ordem é a de candidatura (`queued_at`): quem se candidatou primeiro é
chamado primeiro, separando goleiros e linha (vaga de goleiro só para goleiro).
Chamar o avulso para uma vaga (e gerar a cobrança de R$ 25) depende das regras
de vagas do jogo e fica no serviço de presença (etapa 1.3).

Estas funções servem tanto para o app quanto para o bot da Fase 2
(`source=AttendanceSource.BOT`).
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.models.attendance import Attendance
from app.models.enums import (
    AttendanceSource,
    AttendanceStatus,
    GameStatus,
    PlayerType,
    Position,
    SlotType,
)
from app.models.game import Game
from app.models.player import Player
from app.services.errors import ConflictError, DomainError, NotFoundError

# Status a partir dos quais o avulso pode (re)entrar na fila
_REJOINABLE = {AttendanceStatus.CANCELLED}
# Jogos que ainda aceitam candidaturas
_OPEN_FOR_QUEUE = {GameStatus.DRAFT, GameStatus.OPEN, GameStatus.CLOSED}


def join_queue(
    db: Session,
    game_id: int,
    player_id: int,
    *,
    now: datetime | None = None,
    source: AttendanceSource = AttendanceSource.APP,
) -> Attendance:
    """Coloca o avulso no fim da fila. Se ele já está na fila, nada muda."""
    now = now or now_utc()
    game = _get_game(db, game_id)
    player = db.get(Player, player_id)
    if player is None:
        raise NotFoundError("Jogador não encontrado")
    if player.type != PlayerType.DROP_IN:
        raise DomainError(
            "Só avulsos entram na fila. Mensalistas já têm vaga na lista."
        )
    if not player.active:
        raise DomainError(f"{player.name} está inativo")
    if game.status not in _OPEN_FOR_QUEUE:
        raise DomainError("Este jogo não aceita mais candidaturas")

    attendance = _find(db, game_id, player_id)
    if attendance is None:
        attendance = Attendance(
            game_id=game_id,
            player_id=player_id,
            slot_type=SlotType.DROP_IN,
            status=AttendanceStatus.QUEUED,
            queued_at=now,
            source=source,
        )
        db.add(attendance)
    elif attendance.status == AttendanceStatus.QUEUED:
        return attendance  # idempotente: mantém a posição atual
    elif attendance.status in _REJOINABLE:
        attendance.status = AttendanceStatus.QUEUED
        attendance.queued_at = now  # volta para o fim da fila
        attendance.late_cancellation = False
        attendance.source = source
    else:
        raise ConflictError(f"{player.name} já está na lista deste jogo")

    db.commit()
    db.refresh(attendance)
    return attendance


def leave_queue(db: Session, game_id: int, player_id: int) -> None:
    """Tira o avulso da fila (desistiu antes de ser chamado).

    O registro é apagado: sair da fila não é desmarcação e não entra nas
    estatísticas. Se ele voltar, entra no fim da fila.
    """
    attendance = _find(db, game_id, player_id)
    if attendance is None or attendance.status != AttendanceStatus.QUEUED:
        raise DomainError("Este jogador não está na fila")
    db.delete(attendance)
    db.commit()


def list_queue(
    db: Session, game_id: int, position: Position | None = None
) -> list[Attendance]:
    """Fila na ordem de chamada (primeiro a se candidatar primeiro)."""
    query = (
        select(Attendance)
        .join(Player, Player.id == Attendance.player_id)
        .where(
            Attendance.game_id == game_id,
            Attendance.status == AttendanceStatus.QUEUED,
        )
        .order_by(Attendance.queued_at, Attendance.id)
    )
    if position is not None:
        query = query.where(Player.position == position)
    return list(db.scalars(query))


def next_in_queue(db: Session, game_id: int, position: Position) -> Attendance | None:
    queue = list_queue(db, game_id, position)
    return queue[0] if queue else None


def _get_game(db: Session, game_id: int) -> Game:
    game = db.get(Game, game_id)
    if game is None:
        raise NotFoundError("Jogo não encontrado")
    return game


def _find(db: Session, game_id: int, player_id: int) -> Attendance | None:
    return db.scalar(
        select(Attendance).where(
            Attendance.game_id == game_id, Attendance.player_id == player_id
        )
    )
