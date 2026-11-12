from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.services.errors import ConflictError, DomainError, NotFoundError


class EmailAlreadyUsedError(ConflictError):
    def __init__(self, email: str):
        super().__init__(f"Já existe um organizador com o e-mail {email}")


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


MIN_PASSWORD_LENGTH = 8


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.email)))


def set_user_active(db: Session, user_id: int, active: bool, *, acting_user: User) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Organizador não encontrado")
    if user.id == acting_user.id and not active:
        raise DomainError("Você não pode desativar o próprio acesso")
    user.active = active
    db.commit()
    db.refresh(user)
    return user


def create_user(
    db: Session, email: str, password: str, role: UserRole = UserRole.ORGANIZER
) -> User:
    if "@" not in email or len(email.strip()) < 3:
        raise DomainError("E-mail inválido")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres")
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
