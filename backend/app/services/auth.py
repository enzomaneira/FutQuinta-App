from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User


class EmailAlreadyUsedError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(func.lower(User.email) == normalize_email(email))
    )


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Devolve o usuário se e-mail e senha conferem e a conta está ativa."""
    user = get_user_by_email(db, email)
    if user is None or not user.active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(
    db: Session, email: str, password: str, role: UserRole = UserRole.ORGANIZER
) -> User:
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyUsedError(email)
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
