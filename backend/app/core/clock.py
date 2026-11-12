"""Relógio da aplicação.

As regras de prazo (quinta 12h, quinta 18h etc.) recebem o "agora" por
parâmetro, com padrão em `now_utc()`. Assim os testes simulam qualquer
horário sem mexer no relógio do sistema.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().tz)


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_local(value: datetime) -> datetime:
    """Converte um datetime com fuso (UTC no banco) para o horário local."""
    return value.astimezone(local_tz())
