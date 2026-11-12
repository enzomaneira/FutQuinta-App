"""Perfil com estatísticas, Histórico e tela Início.

Registrado antes do router de jogos para que /games/history não seja
confundido com /games/{game_id}.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.api.routes.finance import charge_out, get_cash
from app.api.routes.games import game_detail, game_summary
from app.core.clock import now_utc
from app.models.charge import Charge
from app.models.enums import ChargeStatus, ChargeType
from app.models.game import Game
from app.models.player import Player
from app.schemas.games import GameSummary
from app.schemas.stats import (
    GameChargesOut,
    HomeOut,
    OpenChargesSummary,
    PaymentOut,
    ProfileOut,
    RecentGameOut,
    StatsOut,
    VenueOut,
)
from app.services import attendance as att
from app.services import billing, games, players, stats
from app.services.schedule import local_date_of
from app.services.settings import get_all_settings

router = APIRouter(tags=["insights"], dependencies=[Depends(get_current_user)])


@router.get("/players/{player_id}/profile", response_model=ProfileOut)
def player_profile(player_id: int, db: DbSession):
    players.get_player(db, player_id)  # 404 se não existir
    profile = stats.player_profile(db, player_id)
    open_rows = billing.list_charges(db, open_only=True, player_id=player_id)
    return ProfileOut(
        stats=StatsOut(**vars(profile.stats)),
        open_charges=[charge_out(db, c, p) for c, p in open_rows],
        payments=[
            PaymentOut(
                charge_id=charge.id,
                charge_type=charge.type,
                reference=charge.reference,
                amount_cents=payment.amount_cents,
                paid_at=payment.paid_at,
                method=payment.method,
            )
            for payment, charge in profile.payments
        ],
        recent_games=[
            RecentGameOut(
                game_id=r.game_id,
                local_date=local_date_of(r.starts_at),
                game_status=r.game_status,
                status=r.status,
                late_cancellation=r.late_cancellation,
            )
            for r in profile.recent
        ],
    )


@router.get("/games/history", response_model=list[GameSummary])
def games_history(db: DbSession, limit: int = Query(default=60, ge=1, le=200)):
    """Jogos que já começaram (mais recentes primeiro)."""
    past = db.scalars(
        select(Game).where(Game.starts_at <= now_utc()).order_by(Game.starts_at.desc()).limit(limit)
    )
    return [game_summary(db, g) for g in past]


@router.get("/games/{game_id}/charges", response_model=GameChargesOut)
def game_charges(game_id: int, db: DbSession):
    """Valores recebidos no jogo: cobranças dos avulsos daquele jogo."""
    att.get_game(db, game_id)
    rows = db.execute(
        select(Charge, Player)
        .join(Player, Player.id == Charge.player_id)
        .where(Charge.game_id == game_id, Charge.type == ChargeType.DROP_IN)
        .order_by(Player.name)
    ).tuples()
    charges = [charge_out(db, c, p) for c, p in rows]
    return GameChargesOut(
        charges=charges,
        received_cents=sum(c.amount_cents for c in charges if c.status == ChargeStatus.PAID),
        expected_cents=sum(c.amount_cents for c in charges if c.status != ChargeStatus.WAIVED),
    )


@router.get("/home", response_model=HomeOut)
def home(db: DbSession):
    """Tudo da tela Início numa chamada só (mais rápido no celular)."""
    values = get_all_settings(db)
    game = games.current_game(db)
    open_rows = billing.list_charges(db, open_only=True)
    open_items = [charge_out(db, c, p) for c, p in open_rows]
    return HomeOut(
        game=game_detail(db, game) if game else None,
        cash=get_cash(db),
        venue=VenueOut(
            name=values["venue_name"],
            address=values["venue_address"],
            lat=float(values["venue_lat"]),
            lng=float(values["venue_lng"]),
        ),
        open_charges=OpenChargesSummary(
            count=len(open_items),
            overdue=sum(1 for c in open_items if c.status == ChargeStatus.OVERDUE),
            total_cents=sum(c.amount_cents for c in open_items),
            items=open_items[:5],
        ),
        pix_key=values["pix_key"],
    )
