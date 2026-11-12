"""Rotinas agendadas. Cada uma abre a própria sessão, é idempotente e loga
o que mudou (ou o erro, sem derrubar o agendador)."""

import logging

from app.core.db import SessionLocal
from app.services.games import run_due_transitions
from app.services.routines import run_finance_routines

logger = logging.getLogger(__name__)


def game_cycle_tick() -> None:
    """Executada a cada minuto. Os horários vêm das Configurações a cada
    execução, então mudanças valem sem reiniciar o servidor.

    - Jogo: abre a lista (terça 10h), libera pendentes (quinta 12h) e
      encerra o jogo (após 23h).
    - Financeiro: gera mensalidades e quadra (dia 1) e marca atrasos (dia 16).
    """
    try:
        with SessionLocal() as db:
            run_due_transitions(db)
    except Exception:
        logger.exception("Falha na rotina do jogo")
    try:
        with SessionLocal() as db:
            run_finance_routines(db)
    except Exception:
        logger.exception("Falha na rotina financeira")
