"""Avulsos: mensalista que trouxe o jogador.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("players", sa.Column("referred_by_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_players_referred_by_id_players",
        "players",
        "players",
        ["referred_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_players_referred_by_id", "players", ["referred_by_id"])


def downgrade() -> None:
    op.drop_index("ix_players_referred_by_id", table_name="players")
    op.drop_constraint("fk_players_referred_by_id_players", "players", type_="foreignkey")
    op.drop_column("players", "referred_by_id")
