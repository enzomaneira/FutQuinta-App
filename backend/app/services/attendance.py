"""Lista semanal: vagas, confirmações, desmarcações, chamada de avulsos.

Regras:
- Cada jogo tem vagas por posição (padrão 2 goleiros + 15 de linha). Vaga de
  goleiro só para goleiro; de linha só para linha.
- Ocupam vaga: confirmados e mensalistas ainda pendentes (vaga garantida até
  o prazo de confirmação). Depois do jogo: compareceu/faltou.
- Desmarcar libera a vaga na hora. Depois do horário de "em cima da hora"
  (padrão quinta 18h) a desmarcação é marcada como `late_cancellation`.
- Avulso confirmado gera cobrança (R$ 25); se desmarcar ou faltar, é isentado.
- Mensalista que desmarcou/perdeu a vaga pode voltar se houver vaga livre,
  sem cobrança extra.

Todas as funções recebem `now` e `source` para o bot da Fase 2 reaproveitar.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.models.attendance import Attendance
from app.models.enums import (
    AttendanceSource,
    AttendanceStatus as S,
    GameStatus,
    PlayerType,
    Position,
    SlotType,
)
from app.models.game import Game
from app.models.player import Player
from app.services import billing
from app.services.errors import ConflictError, DomainError, NotFoundError
from app.services.schedule import late_cancellation_at

IN_SLOT = (S.PENDING, S.CONFIRMED, S.PRESENT, S.ABSENT)
POSITION_LABEL = {Position.GOALKEEPER: "goleiro", Position.FIELD: "linha"}


@dataclass(frozen=True)
class SlotState:
    capacity: int
    confirmed: int  # confirmados (ou compareceu/faltou, depois do jogo)
    pending: int  # mensalistas que ainda não responderam

    @property
    def free(self) -> int:
        return max(self.capacity - self.confirmed - self.pending, 0)


# --- leitura ---


def get_game(db: Session, game_id: int, *, lock: bool = False) -> Game:
    game = db.get(Game, game_id, with_for_update=lock)
    if game is None:
        raise NotFoundError("Jogo não encontrado")
    return game


def slot_usage(db: Session, game: Game) -> dict[Position, SlotState]:
    rows = db.execute(
        select(Player.position, Attendance.status, func.count())
        .join(Player, Player.id == Attendance.player_id)
        .where(Attendance.game_id == game.id, Attendance.status.in_(IN_SLOT))
        .group_by(Player.position, Attendance.status)
    ).all()
    counts: dict[Position, dict[str, int]] = {
        p: {"confirmed": 0, "pending": 0} for p in Position
    }
    for position, status, total in rows:
        key = "pending" if status == S.PENDING else "confirmed"
        counts[position][key] += total
    return {
        Position.GOALKEEPER: SlotState(game.goalkeeper_slots, **counts[Position.GOALKEEPER]),
        Position.FIELD: SlotState(game.field_slots, **counts[Position.FIELD]),
    }


def game_attendances(db: Session, game_id: int) -> list[tuple[Attendance, Player]]:
    return list(
        db.execute(
            select(Attendance, Player)
            .join(Player, Player.id == Attendance.player_id)
            .where(Attendance.game_id == game_id)
        )
        .tuples()
        .all()
    )


def find_attendance(db: Session, game_id: int, player_id: int) -> Attendance | None:
    return db.scalar(
        select(Attendance).where(
            Attendance.game_id == game_id, Attendance.player_id == player_id
        )
    )


# --- ações (cada uma é uma transação) ---


def confirm_player(
    db: Session,
    game_id: int,
    player_id: int,
    *,
    now: datetime | None = None,
    source: AttendanceSource = AttendanceSource.APP,
) -> Attendance:
    """Confirma o jogador. Também é o "chamar" do avulso que está na fila."""
    game = get_game(db, game_id, lock=True)
    attendance = _confirm(db, game, player_id, now or now_utc(), source)
    db.commit()
    db.refresh(attendance)
    return attendance


def cancel_player(
    db: Session,
    game_id: int,
    player_id: int,
    *,
    now: datetime | None = None,
    source: AttendanceSource = AttendanceSource.APP,
) -> Attendance:
    """Desmarca: a vaga fica livre na hora para os avulsos."""
    game = get_game(db, game_id, lock=True)
    attendance = _cancel(db, game, player_id, now or now_utc(), source)
    db.commit()
    db.refresh(attendance)
    return attendance


def call_next(db: Session, game_id: int, position: Position, *, now=None) -> Attendance:
    """Chama o primeiro da fila para uma vaga livre da posição."""
    from app.services.queue import next_in_queue

    queued = next_in_queue(db, game_id, position)
    if queued is None:
        raise DomainError(f"Não há {POSITION_LABEL[position]} na fila")
    return confirm_player(db, game_id, queued.player_id, now=now)


def substitute(
    db: Session, game_id: int, out_player_id: int, in_player_id: int, *, now=None
) -> Attendance:
    """Troca um jogador por outro numa única operação (tudo ou nada)."""
    if out_player_id == in_player_id:
        raise DomainError("Escolha jogadores diferentes")
    now = now or now_utc()
    game = get_game(db, game_id, lock=True)
    try:
        _cancel(db, game, out_player_id, now, AttendanceSource.APP)
        db.flush()
        attendance = _confirm(db, game, in_player_id, now, AttendanceSource.APP)
    except DomainError:
        db.rollback()
        raise
    db.commit()
    db.refresh(attendance)
    return attendance


def set_presence(
    db: Session, game_id: int, player_id: int, present: bool, *, now: datetime | None = None
) -> Attendance:
    """Depois do jogo: corrige compareceu/faltou (o fechamento marca todos
    os confirmados como presentes)."""
    game = get_game(db, game_id, lock=True)
    if game.status != GameStatus.PLAYED:
        raise DomainError("Presença só pode ser marcada depois do jogo")
    attendance = find_attendance(db, game_id, player_id)
    if attendance is None or attendance.status not in (S.CONFIRMED, S.PRESENT, S.ABSENT):
        raise DomainError("Este jogador não estava confirmado neste jogo")
    attendance.status = S.PRESENT if present else S.ABSENT
    if attendance.slot_type == SlotType.DROP_IN:
        if present:
            billing.ensure_drop_in_charge(db, player_id, game, now=now)
        else:
            billing.waive_drop_in_charge(db, player_id, game)
    db.commit()
    db.refresh(attendance)
    return attendance


# --- regras internas (sem commit) ---


def _ensure_editable(game: Game) -> None:
    if game.status == GameStatus.PLAYED:
        raise DomainError("Este jogo já foi realizado")
    if game.status == GameStatus.CANCELLED:
        raise DomainError("Este jogo foi cancelado")


def _confirm(db, game, player_id, now, source) -> Attendance:
    _ensure_editable(game)
    player = db.get(Player, player_id)
    if player is None:
        raise NotFoundError("Jogador não encontrado")
    attendance = find_attendance(db, game.id, player_id)

    if attendance is not None and attendance.status == S.CONFIRMED:
        return attendance  # já confirmado: nada muda
    if attendance is None or attendance.status != S.PENDING:
        # Pendente já tem a vaga garantida; os demais precisam de vaga livre
        if not player.active:
            raise DomainError(f"{player.name} está inativo")
        free = slot_usage(db, game)[player.position].free
        if free <= 0:
            label = POSITION_LABEL[player.position]
            raise ConflictError(
                f"Não há vaga de {label} livre. Alguém precisa desmarcar antes."
            )

    if attendance is None:
        attendance = Attendance(
            game_id=game.id,
            player_id=player_id,
            slot_type=SlotType.MONTHLY if player.type == PlayerType.MONTHLY else SlotType.DROP_IN,
        )
        db.add(attendance)
    attendance.status = S.CONFIRMED
    attendance.responded_at = now
    attendance.late_cancellation = False
    attendance.source = source
    if attendance.slot_type == SlotType.DROP_IN:
        db.flush()
        billing.ensure_drop_in_charge(db, player_id, game, now=now)
    return attendance


def _cancel(db, game, player_id, now, source) -> Attendance:
    _ensure_editable(game)
    attendance = find_attendance(db, game.id, player_id)
    if attendance is not None and attendance.status == S.QUEUED:
        raise DomainError("Este jogador está na fila: use \"Tirar da fila\"")
    if attendance is None or attendance.status not in (S.PENDING, S.CONFIRMED):
        raise DomainError("Este jogador não está na lista deste jogo")
    attendance.status = S.CANCELLED
    attendance.responded_at = now
    attendance.source = source
    # Desmarcar a partir do limite (padrão quinta 18h) é "em cima da hora"
    attendance.late_cancellation = now >= late_cancellation_at(db, game.starts_at)
    if attendance.slot_type == SlotType.DROP_IN:
        billing.waive_drop_in_charge(db, player_id, game)
    return attendance
