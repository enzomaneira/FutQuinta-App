"""Rotinas financeiras periódicas (chamadas pelo agendador a cada minuto).

- Dia de cobrança (padrão dia 1): gera as mensalidades do mês e lança o
  aluguel da quadra. Roda uma vez por mês (registrado em job_runs); se o
  servidor estava fora no dia 1, roda na primeira execução depois.
- Todo dia: cobranças não pagas com vencimento passado viram "atrasadas"
  (mensalidade: dia 16 por padrão; avulso: dia seguinte ao jogo).
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.models.job_run import JobRun
from app.services import billing, cashbox
from app.services.schedule import local_date_of
from app.services.settings import get_setting

logger = logging.getLogger(__name__)

MONTHLY_JOB = "monthly_billing"


@dataclass
class FinanceResult:
    monthly_generated: int | None = None  # None = não era dia de gerar
    court_expense: bool = False
    overdue: int = 0


def run_finance_routines(db: Session, now: datetime | None = None) -> FinanceResult:
    today = local_date_of(now or now_utc())
    result = FinanceResult()

    period = billing.month_reference(today.year, today.month)
    billing_day = int(get_setting(db, "billing_day"))
    already = db.scalar(
        select(JobRun).where(JobRun.name == MONTHLY_JOB, JobRun.period == period)
    )
    if today.day >= billing_day and already is None:
        generated = billing.generate_monthly_fees(db, today.year, today.month)
        court = cashbox.ensure_court_expense(db, today.year, today.month)
        db.add(
            JobRun(
                name=MONTHLY_JOB,
                period=period,
                details={"created": generated.created, "court_expense": court is not None},
            )
        )
        db.commit()
        result.monthly_generated = generated.created
        result.court_expense = court is not None
        logger.info(
            "Mensalidades de %s geradas: %d (quadra lançada: %s)",
            period,
            generated.created,
            court is not None,
        )

    result.overdue = billing.mark_overdue(db, today)
    if result.overdue:
        logger.info("%d cobrança(s) marcada(s) como atrasada(s)", result.overdue)
    return result
