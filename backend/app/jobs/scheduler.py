"""Agendador das rotinas (APScheduler).

Roda dentro do processo da API, por isso o deploy usa UMA réplica.
As rotinas (etapa 1.3/1.4) serão idempotentes: se rodarem duas vezes, por
exemplo durante a troca de versão no Railway, o resultado é o mesmo.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.clock import local_tz
from app.jobs.tasks import game_cycle_tick

logger = logging.getLogger(__name__)


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(
        timezone=local_tz(),
        job_defaults={
            "coalesce": True,  # se acumulou execuções perdidas, roda uma só
            "max_instances": 1,
            "misfire_grace_time": 60 * 60,  # tolera até 1h de atraso
        },
    )
    register_jobs(scheduler)
    return scheduler


def register_jobs(scheduler: BackgroundScheduler) -> None:
    """Registra as rotinas. As cobranças mensais entram na etapa 1.4."""
    # A cada minuto, e uma vez logo na subida (recupera o que ficou para trás)
    scheduler.add_job(
        game_cycle_tick,
        "interval",
        minutes=1,
        id="game_cycle",
        next_run_time=datetime.now(local_tz()),
        replace_existing=True,
    )
    logger.info("Agendador configurado (%d rotinas)", len(scheduler.get_jobs()))
