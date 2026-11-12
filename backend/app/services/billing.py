"""Cobranças. Nesta etapa só a cobrança do avulso (R$ 25 por jogo);
mensalidades, pagamentos e caixa entram na etapa 1.4.

Regra do usuário: avulso que confirma e não vai NÃO é cobrado — a cobrança
vira "isenta" (desde que ainda não tenha sido paga).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.charge import Charge
from app.models.enums import ChargeStatus, ChargeType
from app.models.game import Game
from app.services.schedule import local_date_of
from app.services.settings import get_setting

_OPEN = {ChargeStatus.PENDING, ChargeStatus.OVERDUE}


def drop_in_reference(game: Game) -> str:
    return f"game:{game.id}"


def find_drop_in_charge(db: Session, player_id: int, game: Game) -> Charge | None:
    return db.scalar(
        select(Charge).where(
            Charge.player_id == player_id,
            Charge.type == ChargeType.DROP_IN,
            Charge.reference == drop_in_reference(game),
        )
    )


def ensure_drop_in_charge(db: Session, player_id: int, game: Game) -> Charge:
    """Gera (ou reativa) a cobrança do avulso confirmado. Idempotente."""
    charge = find_drop_in_charge(db, player_id, game)
    if charge is None:
        charge = Charge(
            player_id=player_id,
            game_id=game.id,
            type=ChargeType.DROP_IN,
            reference=drop_in_reference(game),
            amount_cents=int(get_setting(db, "drop_in_fee_cents")),
            due_date=local_date_of(game.starts_at),
            status=ChargeStatus.PENDING,
        )
        db.add(charge)
    elif charge.status == ChargeStatus.WAIVED:
        charge.status = ChargeStatus.PENDING
    return charge


def waive_drop_in_charge(db: Session, player_id: int, game: Game) -> None:
    """Avulso não foi: isenta a cobrança em aberto (pagas ficam como estão)."""
    charge = find_drop_in_charge(db, player_id, game)
    if charge is not None and charge.status in _OPEN:
        charge.status = ChargeStatus.WAIVED
