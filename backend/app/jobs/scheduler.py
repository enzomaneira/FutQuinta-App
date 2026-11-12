"""Agendador das rotinas (APScheduler).

Roda dentro do processo da API, por isso o deploy usa UMA réplica.
As rotinas (etapa 1.3/1.4) serão idempotentes: se rodarem duas vezes, por
exemplo durante a troca de versão no Railway, o resultado é o mesmo.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.clock import local_tz

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
    """Registra as rotinas. Vazio na etapa 1.1; preenchido na 1.3 e 1.4."""
    logger.info("Agendador configurado (%d rotinas)", len(scheduler.get_jobs()))
