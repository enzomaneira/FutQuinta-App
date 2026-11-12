"""Cadastro de jogadores (mensalistas e avulsos).

Regra das vagas garantidas: o número de mensalistas ATIVOS por posição não
pode passar das vagas do jogo (padrão 2 goleiros + 15 de linha), porque cada
mensalista tem uma vaga garantida na lista semanal.
"""

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.charge import Charge
from app.models.enums import PlayerType, Position
from app.models.game import Game
from app.models.player import Player
from app.services.errors import ConflictError, DomainError, NotFoundError
from app.services.phones import normalize_phone
from app.services.settings import get_setting

POSITION_LABEL = {Position.GOALKEEPER: "goleiro", Position.FIELD: "linha"}

@dataclass(frozen=True)
class SlotUsage:
    used: int
    total: int


def monthly_slots(db: Session) -> dict[Position, SlotUsage]:
    """Quantos mensalistas ativos existem por posição, contra as vagas."""
    counts = dict(
        db.execute(
            select(Player.position, func.count())
            .where(Player.type == PlayerType.MONTHLY, Player.active.is_(True))
            .group_by(Player.position)
        ).all()
    )
    return {
        Position.GOALKEEPER: SlotUsage(
            counts.get(Position.GOALKEEPER, 0), get_setting(db, "goalkeeper_slots")
        ),
        Position.FIELD: SlotUsage(
            counts.get(Position.FIELD, 0), get_setting(db, "field_slots")
        ),
    }


def list_players(
    db: Session,
    *,
    type: PlayerType | None = None,
    position: Position | None = None,
    active: bool | None = True,
    search: str | None = None,
) -> list[Player]:
    query = select(Player)
    if type is not None:
        query = query.where(Player.type == type)
    if position is not None:
        query = query.where(Player.position == position)
    if active is not None:
        query = query.where(Player.active.is_(active))
    if search and search.strip():
        term = f"%{search.strip()}%"
        digits = "".join(ch for ch in search if ch.isdigit())
        conditions = [Player.name.ilike(term)]
        if digits:
            conditions.append(Player.phone.like(f"%{digits}%"))
        query = query.where(or_(*conditions))
    return list(db.scalars(query.order_by(func.lower(Player.name), Player.id)))


def get_player(db: Session, player_id: int) -> Player:
    player = db.get(Player, player_id)
    if player is None:
        raise NotFoundError("Jogador não encontrado")
    return player


def create_player(
    db: Session,
    *,
    name: str,
    type: PlayerType,
    position: Position,
    phone: str | None = None,
) -> Player:
    player = Player(
        name=_clean_name(name),
        phone=normalize_phone(phone),
        type=type,
        position=position,
        active=True,
    )
    _check_phone_unique(db, player.phone, exclude_id=None)
    _check_monthly_slot(db, player)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def update_player(db: Session, player_id: int, **changes) -> Player:
    """Atualiza só os campos informados (name, phone, type, position, active).

    `phone=None` apaga o telefone. Em erro de validação nada é alterado.
    """
    unknown = set(changes) - {"name", "phone", "type", "position", "active"}
    if unknown:
        raise TypeError(f"Campos desconhecidos: {sorted(unknown)}")

    player = get_player(db, player_id)
    try:
        # no_autoflush: as consultas de validação não podem gravar a alteração
        # antes da hora (o banco recusaria com erro genérico de unicidade)
        with db.no_autoflush:
            if "name" in changes:
                player.name = _clean_name(changes["name"])
            if "phone" in changes:
                player.phone = normalize_phone(changes["phone"])
                _check_phone_unique(db, player.phone, exclude_id=player.id)
            for field in ("type", "position", "active"):
                if field in changes:
                    setattr(player, field, changes[field])
            # Valida a vaga com o estado final (ex.: avulso virando mensalista)
            _check_monthly_slot(db, player)
    except DomainError:
        db.rollback()  # descarta a alteração parcial em memória
        raise
    db.commit()
    db.refresh(player)
    return player


def has_history(db: Session, player_id: int) -> bool:
    """True se o jogador já aparece em algum jogo, cobrança ou coletes."""
    return any(
        db.scalar(select(func.count()).select_from(model).where(column == player_id))
        for model, column in (
            (Attendance, Attendance.player_id),
            (Charge, Charge.player_id),
            (Game, Game.bib_player_id),
        )
    )


def delete_player(db: Session, player_id: int) -> None:
    """Exclui só cadastros sem histórico (ex.: criado por engano).
    Quem já tem histórico deve ser desativado, para não perder estatísticas."""
    player = get_player(db, player_id)
    if has_history(db, player_id):
        raise ConflictError(
            "Este jogador já tem histórico de jogos ou pagamentos. Desative em vez de excluir."
        )
    db.delete(player)
    db.commit()


# --- validações internas ---


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise DomainError("Informe o nome do jogador")
    return cleaned


def _check_phone_unique(db: Session, phone: str | None, exclude_id: int | None) -> None:
    if phone is None:
        return
    query = select(Player).where(Player.phone == phone)
    if exclude_id is not None:
        query = query.where(Player.id != exclude_id)
    other = db.scalar(query)
    if other is not None:
        raise ConflictError(f"Este telefone já está cadastrado para {other.name}")


def _check_monthly_slot(db: Session, player: Player) -> None:
    if player.type != PlayerType.MONTHLY or not player.active:
        return
    query = select(func.count()).where(
        Player.type == PlayerType.MONTHLY,
        Player.active.is_(True),
        Player.position == player.position,
    )
    if player.id is not None:
        query = query.where(Player.id != player.id)
    others = db.scalar(query) or 0
    limit_key = (
        "goalkeeper_slots" if player.position == Position.GOALKEEPER else "field_slots"
    )
    limit = get_setting(db, limit_key)
    if others >= limit:
        label = POSITION_LABEL[player.position]
        raise ConflictError(
            f"Já existem {others} mensalistas {label} ativos (limite {limit}). "
            "Desative um deles ou cadastre como avulso."
        )
