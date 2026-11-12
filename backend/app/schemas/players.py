from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlayerType, Position


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    type: PlayerType
    position: Position


class PlayerUpdate(BaseModel):
    """Todos opcionais: só os campos enviados são alterados."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    type: PlayerType | None = None
    position: Position | None = None
    active: bool | None = None


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None
    type: PlayerType
    position: Position
    active: bool
    created_at: datetime


class PlayerDetail(PlayerOut):
    # Sem histórico pode ser excluído; com histórico, só desativado
    can_delete: bool


class SlotUsageOut(BaseModel):
    used: int
    total: int


class MonthlySlotsOut(BaseModel):
    goalkeeper: SlotUsageOut
    field: SlotUsageOut
