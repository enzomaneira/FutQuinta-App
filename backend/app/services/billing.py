"""Cobranças e pagamentos.

- Mensalidade: uma por mensalista ativo por mês (referência "AAAA-MM"),
  gerada no dia de cobrança (padrão dia 1), vencendo no dia configurado
  (padrão 15). O mensalista deve a mensalidade mesmo se desmarcar ou perder
  a vaga.
- Avulso: R$ 25 por jogo (referência "game:<id>"), gerada ao confirmar.
  Avulso que não vai não é cobrado: a cobrança vira "isenta".
- Cobrança não paga depois do vencimento vira "atrasada".

As funções recebem `now`/`today` para testes e para o bot da Fase 2
(pagamento por comprovante com aprovação manual).
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.models.charge import Charge
from app.models.enums import (
    ChargeStatus,
    ChargeType,
    PaymentMethod,
    PaymentSource,
    PlayerType,
)
from app.models.game import Game
from app.models.payment import Payment
from app.models.player import Player
from app.services.errors import DomainError, NotFoundError
from app.services.schedule import local_date_of
from app.services.settings import get_all_settings, get_setting

_OPEN = (ChargeStatus.PENDING, ChargeStatus.OVERDUE)


def month_reference(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def parse_month(reference: str) -> tuple[int, int]:
    try:
        year, month = (int(part) for part in reference.split("-"))
        date(year, month, 1)
    except ValueError:
        raise DomainError("Mês inválido (use AAAA-MM)")
    return year, month


def unpaid_status(charge: Charge, today: date) -> ChargeStatus:
    """Situação de uma cobrança não paga: atrasada depois do vencimento."""
    return ChargeStatus.OVERDUE if charge.due_date < today else ChargeStatus.PENDING


# --- avulso ---


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


def ensure_drop_in_charge(
    db: Session, player_id: int, game: Game, *, now: datetime | None = None
) -> Charge:
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
        charge.status = unpaid_status(charge, local_date_of(now or now_utc()))
    return charge


def waive_drop_in_charge(db: Session, player_id: int, game: Game) -> None:
    """Avulso não foi: isenta a cobrança em aberto (pagas ficam como estão)."""
    charge = find_drop_in_charge(db, player_id, game)
    if charge is not None and charge.status in _OPEN:
        charge.status = ChargeStatus.WAIVED


# --- mensalidades ---


@dataclass
class MonthlyResult:
    reference: str
    created: int


def generate_monthly_fees(db: Session, year: int, month: int) -> MonthlyResult:
    """Gera a mensalidade do mês para cada mensalista ativo que ainda não tem.
    Idempotente: rodar de novo só cria as que faltam (ex.: mensalista novo)."""
    values = get_all_settings(db)
    reference = month_reference(year, month)
    due = date(year, month, int(values["monthly_due_day"]))
    already = set(
        db.scalars(
            select(Charge.player_id).where(
                Charge.type == ChargeType.MONTHLY_FEE, Charge.reference == reference
            )
        )
    )
    players = db.scalars(
        select(Player).where(Player.type == PlayerType.MONTHLY, Player.active.is_(True))
    )
    created = 0
    for player in players:
        if player.id in already:
            continue
        db.add(
            Charge(
                player_id=player.id,
                type=ChargeType.MONTHLY_FEE,
                reference=reference,
                amount_cents=int(values["monthly_fee_cents"]),
                due_date=due,
                status=ChargeStatus.PENDING,
            )
        )
        created += 1
    db.commit()
    return MonthlyResult(reference=reference, created=created)


def mark_overdue(db: Session, today: date) -> int:
    """Dia 16 (padrão): cobranças não pagas vencidas viram "atrasadas"."""
    result = db.execute(
        update(Charge)
        .where(Charge.status == ChargeStatus.PENDING, Charge.due_date < today)
        .values(status=ChargeStatus.OVERDUE)
    )
    db.commit()
    return result.rowcount or 0


# --- pagamentos ---


def get_charge(db: Session, charge_id: int, *, lock: bool = False) -> Charge:
    charge = db.get(Charge, charge_id, with_for_update=lock)
    if charge is None:
        raise NotFoundError("Cobrança não encontrada")
    return charge


def register_payment(
    db: Session,
    charge_id: int,
    *,
    method: PaymentMethod = PaymentMethod.PIX,
    paid_at: datetime | None = None,
    source: PaymentSource = PaymentSource.MANUAL,
    receipt_url: str | None = None,
) -> Payment:
    """Marca a cobrança como paga (valor integral)."""
    charge = get_charge(db, charge_id, lock=True)
    if charge.status == ChargeStatus.PAID:
        raise DomainError("Esta cobrança já está paga")
    if charge.status == ChargeStatus.WAIVED:
        raise DomainError("Esta cobrança está isenta. Tire a isenção antes de receber.")
    payment = Payment(
        charge_id=charge.id,
        amount_cents=charge.amount_cents,
        paid_at=paid_at or now_utc(),
        method=method,
        source=source,
        receipt_url=receipt_url,
    )
    db.add(payment)
    charge.status = ChargeStatus.PAID
    db.commit()
    db.refresh(payment)
    return payment


def undo_payment(db: Session, charge_id: int, *, today: date | None = None) -> Charge:
    """Desfaz um pagamento marcado por engano (o caixa volta junto)."""
    charge = get_charge(db, charge_id, lock=True)
    if charge.status != ChargeStatus.PAID:
        raise DomainError("Esta cobrança não está paga")
    db.execute(delete(Payment).where(Payment.charge_id == charge.id))
    charge.status = unpaid_status(charge, today or local_date_of(now_utc()))
    db.commit()
    return charge


def waive(db: Session, charge_id: int) -> Charge:
    """Isenta a cobrança (ex.: mensalista que entrou no meio do mês)."""
    charge = get_charge(db, charge_id, lock=True)
    if charge.status == ChargeStatus.PAID:
        raise DomainError("Cobrança paga não pode ser isentada. Desfaça o pagamento antes.")
    charge.status = ChargeStatus.WAIVED
    db.commit()
    return charge


def unwaive(db: Session, charge_id: int, *, today: date | None = None) -> Charge:
    charge = get_charge(db, charge_id, lock=True)
    if charge.status != ChargeStatus.WAIVED:
        raise DomainError("Esta cobrança não está isenta")
    charge.status = unpaid_status(charge, today or local_date_of(now_utc()))
    db.commit()
    return charge


# --- consultas ---


def list_charges(
    db: Session,
    *,
    type: ChargeType | None = None,
    reference: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    open_only: bool = False,
    player_id: int | None = None,
) -> list[tuple[Charge, Player]]:
    query = select(Charge, Player).join(Player, Player.id == Charge.player_id)
    if type is not None:
        query = query.where(Charge.type == type)
    if reference is not None:
        query = query.where(Charge.reference == reference)
    if due_from is not None:
        query = query.where(Charge.due_date >= due_from)
    if due_to is not None:
        query = query.where(Charge.due_date <= due_to)
    if open_only:
        query = query.where(Charge.status.in_(_OPEN))
    if player_id is not None:
        query = query.where(Charge.player_id == player_id)
    return list(db.execute(query.order_by(Charge.due_date, Player.name)).tuples())


def last_payment(db: Session, charge_id: int) -> Payment | None:
    return db.scalar(
        select(Payment)
        .where(Payment.charge_id == charge_id)
        .order_by(Payment.paid_at.desc())
        .limit(1)
    )


def payment_status_by_player(db: Session) -> dict[int, str]:
    """Situação de cada jogador: "overdue" se tem algo atrasado, "pending" se
    tem algo em aberto ainda no prazo. Jogadores sem pendência não aparecem."""
    rows = db.execute(
        select(Charge.player_id, Charge.status).where(Charge.status.in_(_OPEN))
    ).all()
    result: dict[int, str] = {}
    for player_id, status in rows:
        if status == ChargeStatus.OVERDUE or result.get(player_id) is None:
            result[player_id] = status.value
    return result
