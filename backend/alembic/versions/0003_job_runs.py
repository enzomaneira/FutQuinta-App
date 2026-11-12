"""Registro de rotinas periódicas (mensalidades do mês etc.).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12
"""

from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column(
            "ran_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("details", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_job_runs"),
        sa.UniqueConstraint("name", "period", name="uq_job_runs_name_period"),
    )

    # Implantação no meio do mês: não gera sozinho as mensalidades do mês
    # corrente (podem já ter sido cobradas fora do app). A geração automática
    # começa no próximo mês; o mês atual pode ser gerado pelo botão no app.
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    op.execute(
        sa.text(
            "INSERT INTO job_runs (name, period, details) "
            "VALUES ('monthly_billing', :period, CAST(:details AS JSONB))"
        ).bindparams(
            period=f"{now.year:04d}-{now.month:02d}",
            details='{"skipped": "implantação"}',
        )
    )


def downgrade() -> None:
    op.drop_table("job_runs")
