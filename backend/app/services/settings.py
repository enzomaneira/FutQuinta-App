"""Configurações de negócio (valores, horários, prazos, local).

Os padrões abaixo valem enquanto o organizador não alterar nada na tela de
Configurações. A migration inicial grava esses valores no banco.
Horários são locais (America/Sao_Paulo); dias da semana: segunda=0 ... domingo=6.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.setting import Setting
from app.services.errors import DomainError

DEFAULTS: dict[str, Any] = {
    # Local
    "venue_name": "Quadra de quinta",
    "venue_address": "Rua Dona Brígida, 375 - Vila Mariana, São Paulo - SP",
    # Coordenadas aproximadas: confira/ajuste na tela de Configurações
    "venue_lat": -23.5899,
    "venue_lng": -46.6355,
    # Jogo
    "game_weekday": 3,  # quinta
    "game_start_time": "21:30",
    "game_end_time": "23:00",
    "goalkeeper_slots": 2,
    "field_slots": 15,
    # Lista semanal (relativa ao dia do jogo)
    "list_open_days_before": 2,  # terça
    "list_open_time": "10:00",
    "confirmation_deadline_time": "12:00",  # no dia do jogo
    "late_cancellation_time": "18:00",  # no dia do jogo
    # Valores (centavos)
    "monthly_fee_cents": 5900,
    "drop_in_fee_cents": 2500,
    "court_monthly_cents": 0,  # aluguel mensal da quadra: definir em Configurações
    "initial_cash_cents": 24500,  # saldo inicial do caixa
    # Cobrança
    "billing_day": 1,  # dia em que as mensalidades são geradas
    "monthly_due_day": 15,  # vencimento (no dia seguinte vira "atrasado")
    # Pix (exibido para os jogadores; integração só na Fase 2)
    "pix_key": "",
}


def get_setting(db: Session, key: str) -> Any:
    row = db.get(Setting, key)
    if row is not None:
        return row.value
    if key in DEFAULTS:
        return DEFAULTS[key]
    raise KeyError(f"Configuração desconhecida: {key}")


def get_all_settings(db: Session) -> dict[str, Any]:
    values = dict(DEFAULTS)
    for row in db.query(Setting).all():
        values[row.key] = row.value
    return values


def update_settings(db: Session, changes: dict[str, Any]) -> dict[str, Any]:
    """Grava as configurações alteradas (chaves já validadas pelo schema).

    Vale para os próximos jogos: jogos já criados mantêm horários e vagas.
    """
    unknown = set(changes) - set(DEFAULTS)
    if unknown:
        raise KeyError(f"Configurações desconhecidas: {sorted(unknown)}")
    merged = {**get_all_settings(db), **changes}
    if merged["game_start_time"] == merged["game_end_time"]:
        raise DomainError("O horário de fim precisa ser diferente do início")
    if merged["confirmation_deadline_time"] > merged["late_cancellation_time"]:
        raise DomainError(
            "O prazo de confirmação precisa ser antes do horário de desistência em cima da hora"
        )
    for key, value in changes.items():
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_all_settings(db)
