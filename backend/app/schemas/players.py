from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlayerType, Position


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    type: PlayerType
    position: Position
    referred_by_id: int | None = None  # mensalista que trouxe (só avulso)


class PlayerUpdate(BaseModel):
    """Todos opcionais: só os campos enviados são alterados."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    type: PlayerType | None = None
    position: Position | None = None
    active: bool | None = None
    referred_by_id: int | None = None  # null tira o vínculo


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None
    type: PlayerType
    position: Position
    active: bool
    created_at: datetime
    # "ok" (em dia), "pending" (em aberto no prazo) ou "overdue" (atrasado)
    payment_status: Literal["ok", "pending", "overdue"] = "ok"
    referred_by_id: int | None = None
    referred_by_name: str | None = None  # mensalista que trouxe o avulso


class PlayerDetail(PlayerOut):
    # Sem histórico pode ser excluído; com histórico, só desativado
    can_delete: bool


class SlotUsageOut(BaseModel):
    used: int
    total: int


class MonthlySlotsOut(BaseModel):
    goalkeeper: SlotUsageOut
    field: SlotUsageOut
