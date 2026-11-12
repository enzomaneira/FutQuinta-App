"""Utilitários de teste: horários locais e montagem de elenco."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.models.enums import PlayerType, Position

SP = ZoneInfo("America/Sao_Paulo")
GAME_DAY = date(2026, 11, 19)  # quinta-feira


def sp(day: int, hour: int, minute: int = 0, month: int = 11) -> datetime:
    """Horário de São Paulo em novembro/2026 (ex.: sp(19, 18) = quinta 18h)."""
    return datetime(2026, month, day, hour, minute, tzinfo=SP)


def make_squad(make_player, goalkeepers: int = 2, field: int = 15) -> dict:
    """Cria os mensalistas: por padrão 2 goleiros + 15 de linha."""
    gks = [
        make_player(f"Goleiro {i}", type=PlayerType.MONTHLY, position=Position.GOALKEEPER)
        for i in range(1, goalkeepers + 1)
    ]
    fields = [
        make_player(f"Linha {i:02d}", type=PlayerType.MONTHLY, position=Position.FIELD)
        for i in range(1, field + 1)
    ]
    return {"gk": gks, "field": fields}
