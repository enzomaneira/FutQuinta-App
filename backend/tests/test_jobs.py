"""Agendador: rotina registrada e falhas que não derrubam o processo."""

import logging

from app.jobs import tasks
from app.jobs.scheduler import build_scheduler


def test_agendador_registra_a_rotina_de_um_minuto():
    scheduler = build_scheduler()
    jobs = {job.id: job for job in scheduler.get_jobs()}
    assert set(jobs) == {"game_cycle"}
    assert jobs["game_cycle"].trigger.interval.total_seconds() == 60
    assert str(scheduler.timezone) == "America/Sao_Paulo"


def test_falha_numa_rotina_nao_impede_a_outra(monkeypatch, caplog):
    called = []

    def broken(db):
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr(tasks, "run_due_transitions", broken)
    monkeypatch.setattr(tasks, "run_finance_routines", lambda db: called.append(True))
    with caplog.at_level(logging.ERROR):
        tasks.game_cycle_tick()  # não pode lançar exceção
    assert called == [True]
    assert "Falha na rotina do jogo" in caplog.text
