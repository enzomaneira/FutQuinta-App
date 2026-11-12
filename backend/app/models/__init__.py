"""Importa todos os modelos para o metadata ficar completo (usado pelo Alembic)."""

from app.models.attendance import Attendance
from app.models.charge import Charge
from app.models.expense import Expense
from app.models.game import Game
from app.models.payment import Payment
from app.models.player import Player
from app.models.setting import Setting
from app.models.user import User

__all__ = [
    "Attendance",
    "Charge",
    "Expense",
    "Game",
    "Payment",
    "Player",
    "Setting",
    "User",
]
