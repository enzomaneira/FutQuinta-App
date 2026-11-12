"""Configurações de negócio e organizadores."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, get_current_user
from app.models.enums import UserRole
from app.schemas.auth import UserOut
from app.schemas.settings import SettingsUpdate
from app.services import auth as auth_service
from app.services.settings import get_all_settings, update_settings

router = APIRouter(tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("/settings")
def read_settings(db: DbSession) -> dict[str, Any]:
    return get_all_settings(db)


@router.patch("/settings")
def patch_settings(body: SettingsUpdate, db: DbSession) -> dict[str, Any]:
    return update_settings(db, body.model_dump(exclude_unset=True, exclude_none=True))


# --- organizadores ---


class UserListOut(UserOut):
    active: bool


class UserCreate(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=200)
    admin: bool = False


class UserPatch(BaseModel):
    active: bool


def _require_admin(user) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Só administradores podem gerenciar organizadores"
        )


@router.get("/users", response_model=list[UserListOut])
def list_users(db: DbSession):
    return auth_service.list_users(db)


@router.post("/users", response_model=UserListOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: DbSession, user: CurrentUser):
    _require_admin(user)
    role = UserRole.ADMIN if body.admin else UserRole.ORGANIZER
    return auth_service.create_user(db, body.email, body.password, role)


@router.patch("/users/{user_id}", response_model=UserListOut)
def patch_user(user_id: int, body: UserPatch, db: DbSession, user: CurrentUser):
    _require_admin(user)
    return auth_service.set_user_active(db, user_id, body.active, acting_user=user)
