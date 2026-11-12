"""Rotas de jogadores. Só traduzem HTTP <-> serviço; as regras estão em
app/services/players.py."""

from typing import Literal

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DbSession, get_current_user
from app.models.enums import PlayerType, Position
from app.schemas.players import (
    MonthlySlotsOut,
    PlayerCreate,
    PlayerDetail,
    PlayerOut,
    PlayerUpdate,
    SlotUsageOut,
)
from app.services import players as service

router = APIRouter(
    prefix="/players", tags=["players"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[PlayerOut])
def list_players(
    db: DbSession,
    type: PlayerType | None = None,
    position: Position | None = None,
    status: Literal["active", "inactive", "all"] = "active",
    q: str | None = None,
):
    active = {"active": True, "inactive": False, "all": None}[status]
    return service.list_players(
        db, type=type, position=position, active=active, search=q
    )


@router.get("/monthly-slots", response_model=MonthlySlotsOut)
def monthly_slots(db: DbSession):
    usage = service.monthly_slots(db)
    return MonthlySlotsOut(
        goalkeeper=SlotUsageOut(**vars(usage[Position.GOALKEEPER])),
        field=SlotUsageOut(**vars(usage[Position.FIELD])),
    )


@router.post("", response_model=PlayerOut, status_code=status.HTTP_201_CREATED)
def create_player(body: PlayerCreate, db: DbSession):
    return service.create_player(db, **body.model_dump())


@router.get("/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, db: DbSession):
    player = service.get_player(db, player_id)
    return PlayerDetail(
        **PlayerOut.model_validate(player).model_dump(),
        can_delete=not service.has_history(db, player_id),
    )


@router.patch("/{player_id}", response_model=PlayerOut)
def update_player(player_id: int, body: PlayerUpdate, db: DbSession):
    changes = body.model_dump(exclude_unset=True)
    # `phone: null` apaga o telefone; nos demais campos, null é ignorado
    changes = {k: v for k, v in changes.items() if v is not None or k == "phone"}
    return service.update_player(db, player_id, **changes)


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(player_id: int, db: DbSession):
    service.delete_player(db, player_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
