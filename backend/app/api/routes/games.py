"""Rotas do jogo e do calendário. Só traduzem HTTP <-> serviços; as regras
ficam em app/services/{games,attendance,queue}.py."""

import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import DbSession, get_current_user
from app.core.clock import now_utc, to_local
from app.models.enums import AttendanceStatus as S, GameStatus, Position
from app.models.game import Game
from app.models.player import Player
from app.schemas.games import (
    AttendanceOut,
    BibIn,
    BibPlayerOut,
    CalendarOut,
    CallNextIn,
    CreateGameIn,
    GameDetail,
    GameSummary,
    PresenceIn,
    QueueIn,
    SlotOut,
    SubstituteIn,
)
from app.services import attendance as att
from app.services import games as games_service
from app.services import queue as queue_service
from app.services import players as players_service
from app.services.attendance import IN_SLOT, POSITION_LABEL
from app.services.schedule import late_cancellation_at, local_date_of
from app.services.settings import get_setting

router = APIRouter(tags=["games"], dependencies=[Depends(get_current_user)])

_STATUS_ORDER = {S.CONFIRMED: 0, S.PRESENT: 0, S.ABSENT: 1, S.PENDING: 2}


# --- leitura ---


@router.get("/calendar", response_model=CalendarOut)
def get_calendar(db: DbSession, month: str | None = None):
    """Jogos de um mês ("AAAA-MM"; padrão: mês atual)."""
    if month:
        try:
            year, mon = (int(part) for part in month.split("-"))
            first = date(year, mon, 1)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mês inválido (use AAAA-MM)")
    else:
        today = local_date_of(now_utc())
        first = today.replace(day=1)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    games = games_service.list_games(db, first, last)
    return CalendarOut(
        month=first.strftime("%Y-%m"),
        game_weekday=int(get_setting(db, "game_weekday")),
        due_day=int(get_setting(db, "monthly_due_day")),
        games=[game_summary(db, g) for g in games],
    )


@router.get("/games/current", response_model=GameDetail | None)
def get_current_game(db: DbSession):
    game = games_service.current_game(db)
    return game_detail(db, game) if game else None


@router.get("/games/{game_id}", response_model=GameDetail)
def get_game(game_id: int, db: DbSession):
    return game_detail(db, att.get_game(db, game_id))


# --- jogo ---


@router.post("/games", response_model=GameDetail, status_code=status.HTTP_201_CREATED)
def create_game(body: CreateGameIn, db: DbSession):
    return game_detail(db, games_service.create_game(db, body.date))


@router.post("/games/{game_id}/close", response_model=GameDetail)
def close_list(game_id: int, db: DbSession):
    return game_detail(db, games_service.close_list(db, game_id))


@router.post("/games/{game_id}/reopen", response_model=GameDetail)
def reopen_list(game_id: int, db: DbSession):
    return game_detail(db, games_service.reopen_list(db, game_id))


@router.post("/games/{game_id}/cancel", response_model=GameDetail)
def cancel_game(game_id: int, db: DbSession):
    return game_detail(db, games_service.cancel_game(db, game_id))


@router.put("/games/{game_id}/bib", response_model=GameDetail)
def set_bib(game_id: int, body: BibIn, db: DbSession):
    return game_detail(db, games_service.set_bib_player(db, game_id, body.player_id))


# --- lista ---


@router.post("/games/{game_id}/players/{player_id}/confirm", response_model=GameDetail)
def confirm(game_id: int, player_id: int, db: DbSession):
    att.confirm_player(db, game_id, player_id)
    return game_detail(db, att.get_game(db, game_id))


@router.post("/games/{game_id}/players/{player_id}/cancel", response_model=GameDetail)
def cancel(game_id: int, player_id: int, db: DbSession):
    att.cancel_player(db, game_id, player_id)
    return game_detail(db, att.get_game(db, game_id))


@router.post("/games/{game_id}/players/{player_id}/presence", response_model=GameDetail)
def presence(game_id: int, player_id: int, body: PresenceIn, db: DbSession):
    att.set_presence(db, game_id, player_id, body.present)
    return game_detail(db, att.get_game(db, game_id))


@router.post("/games/{game_id}/substitute", response_model=GameDetail)
def substitute(game_id: int, body: SubstituteIn, db: DbSession):
    att.substitute(db, game_id, body.out_player_id, body.in_player_id)
    return game_detail(db, att.get_game(db, game_id))


@router.post("/games/{game_id}/queue", response_model=GameDetail)
def join_queue(game_id: int, body: QueueIn, db: DbSession):
    queue_service.join_queue(db, game_id, body.player_id)
    return game_detail(db, att.get_game(db, game_id))


@router.delete("/games/{game_id}/queue/{player_id}", response_model=GameDetail)
def leave_queue(game_id: int, player_id: int, db: DbSession):
    queue_service.leave_queue(db, game_id, player_id)
    return game_detail(db, att.get_game(db, game_id))


@router.post("/games/{game_id}/call-next", response_model=GameDetail)
def call_next(game_id: int, body: CallNextIn, db: DbSession):
    att.call_next(db, game_id, body.position)
    return game_detail(db, att.get_game(db, game_id))


# --- montagem das respostas ---


def game_summary(db: Session, game: Game) -> GameSummary:
    usage = att.slot_usage(db, game)
    return GameSummary(**_summary_fields(game, usage))


def _summary_fields(game: Game, usage) -> dict:
    return dict(
        id=game.id,
        status=game.status,
        local_date=local_date_of(game.starts_at),
        start_time=to_local(game.starts_at).strftime("%H:%M"),
        end_time=to_local(game.ends_at).strftime("%H:%M"),
        starts_at=game.starts_at,
        occupied=sum(s.confirmed + s.pending for s in usage.values()),
        capacity=sum(s.capacity for s in usage.values()),
    )


def game_detail(db: Session, game: Game) -> GameDetail:
    db.refresh(game)
    now = now_utc()
    usage = att.slot_usage(db, game)
    rows = att.game_attendances(db, game.id)

    lineup: dict[Position, list[AttendanceOut]] = {p: [] for p in Position}
    queue: dict[Position, list[AttendanceOut]] = {p: [] for p in Position}
    out: list[AttendanceOut] = []
    referrers = players_service.referrer_names(db, [player for _, player in rows])
    for attendance, player in rows:
        item = _attendance_out(attendance, player)
        item.referred_by_name = referrers.get(player.id)
        if attendance.status in IN_SLOT:
            lineup[player.position].append(item)
        elif attendance.status == S.QUEUED:
            queue[player.position].append(item)
        else:
            out.append(item)

    for items in lineup.values():
        items.sort(key=lambda a: (_STATUS_ORDER.get(a.status, 9), a.name.lower()))
    for items in queue.values():
        items.sort(key=lambda a: (a.queued_at, a.player_id))
        for index, item in enumerate(items, start=1):
            item.queue_position = index
    out.sort(key=lambda a: a.responded_at or game.starts_at, reverse=True)

    bib = db.get(Player, game.bib_player_id) if game.bib_player_id else None
    editable = game.status in (GameStatus.DRAFT, GameStatus.OPEN, GameStatus.CLOSED)
    return GameDetail(
        **_summary_fields(game, usage),
        ends_at=game.ends_at,
        confirmation_deadline=game.confirmation_deadline,
        late_cancellation_at=late_cancellation_at(db, game.starts_at),
        deadline_passed=now >= game.confirmation_deadline,
        editable=editable,
        bib_player=BibPlayerOut(id=bib.id, name=bib.name) if bib else None,
        slots={
            p: SlotOut(capacity=s.capacity, confirmed=s.confirmed, pending=s.pending, free=s.free)
            for p, s in usage.items()
        },
        alerts=_alerts(game, usage, queue, editable),
        lineup=lineup,
        queue=queue,
        out=out,
    )


def _alerts(game, usage, queue, editable) -> list[str]:
    if not editable:
        return []
    alerts = []
    gk = usage[Position.GOALKEEPER]
    missing_gk = gk.capacity - gk.confirmed
    if missing_gk == 1:
        alerts.append("Falta 1 goleiro confirmado")
    elif missing_gk > 1:
        alerts.append(f"Faltam {missing_gk} goleiros confirmados")
    pending = sum(s.pending for s in usage.values())
    if pending == 1:
        alerts.append("1 mensalista ainda não respondeu")
    elif pending > 1:
        alerts.append(f"{pending} mensalistas ainda não responderam")
    for position, state in usage.items():
        if state.free and queue[position]:
            label = POSITION_LABEL[position]
            vagas = f"1 vaga de {label} livre" if state.free == 1 else f"{state.free} vagas de {label} livres"
            alerts.append(f"{vagas}: chame da fila")
    return alerts


def _attendance_out(attendance, player) -> AttendanceOut:
    return AttendanceOut(
        player_id=player.id,
        name=player.name,
        position=player.position,
        player_type=player.type,
        status=attendance.status,
        slot_type=attendance.slot_type,
        late_cancellation=attendance.late_cancellation,
        responded_at=attendance.responded_at,
        queued_at=attendance.queued_at,
    )
