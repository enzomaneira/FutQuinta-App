"""Esquema inicial: todas as tabelas da Fase 1 e configurações padrão.

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enums são guardados como VARCHAR(20) (ver app/models/enums.py)
ENUM = sa.String(20)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", ENUM, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("type", ENUM, nullable=False),
        sa.Column("position", ENUM, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_players"),
        sa.UniqueConstraint("phone", name="uq_players_phone"),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", ENUM, nullable=False),
        sa.Column("bib_player_id", sa.Integer(), nullable=True),
        sa.Column("confirmation_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("goalkeeper_slots", sa.Integer(), nullable=False),
        sa.Column("field_slots", sa.Integer(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_games"),
        sa.UniqueConstraint("starts_at", name="uq_games_starts_at"),
        sa.ForeignKeyConstraint(
            ["bib_player_id"],
            ["players.id"],
            name="fk_games_bib_player_id_players",
            ondelete="SET NULL",
        ),
    )

    op.create_table(
        "attendances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("status", ENUM, nullable=False),
        sa.Column("slot_type", ENUM, nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("late_cancellation", sa.Boolean(), nullable=False),
        sa.Column("source", ENUM, nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_attendances"),
        sa.UniqueConstraint(
            "game_id", "player_id", name="uq_attendances_game_id_player_id"
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name="fk_attendances_game_id_games",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_attendances_player_id_players",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_attendances_game_id", "attendances", ["game_id"])
    op.create_index("ix_attendances_player_id", "attendances", ["player_id"])

    op.create_table(
        "charges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=True),
        sa.Column("type", ENUM, nullable=False),
        sa.Column("reference", sa.String(30), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", ENUM, nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_charges"),
        sa.UniqueConstraint(
            "player_id",
            "type",
            "reference",
            name="uq_charges_player_id_type_reference",
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_charges_player_id_players",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name="fk_charges_game_id_games",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_charges_player_id", "charges", ["player_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("charge_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", ENUM, nullable=False),
        sa.Column("source", ENUM, nullable=False),
        sa.Column("receipt_url", sa.String(500), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.ForeignKeyConstraint(
            ["charge_id"],
            ["charges.id"],
            name="fk_payments_charge_id_charges",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_payments_charge_id", "payments", ["charge_id"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("category", ENUM, nullable=False),
        sa.Column("type", ENUM, nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(30), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
        sa.UniqueConstraint(
            "category", "reference", name="uq_expenses_category_reference"
        ),
    )

    settings_table = op.create_table(
        "settings",
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_settings"),
    )

    # Valores padrão (cópia fixa de app/services/settings.py DEFAULTS na data
    # desta migration; mudanças futuras de padrão vão em novas migrations)
    op.bulk_insert(
        settings_table,
        [
            {"key": "venue_name", "value": "Quadra de quinta"},
            {
                "key": "venue_address",
                "value": "Rua Dona Brígida, 375 - Vila Mariana, São Paulo - SP",
            },
            {"key": "venue_lat", "value": -23.5899},
            {"key": "venue_lng", "value": -46.6355},
            {"key": "game_weekday", "value": 3},
            {"key": "game_start_time", "value": "21:30"},
            {"key": "game_end_time", "value": "23:00"},
            {"key": "goalkeeper_slots", "value": 2},
            {"key": "field_slots", "value": 15},
            {"key": "list_open_days_before", "value": 2},
            {"key": "list_open_time", "value": "10:00"},
            {"key": "confirmation_deadline_time", "value": "12:00"},
            {"key": "late_cancellation_time", "value": "18:00"},
            {"key": "monthly_fee_cents", "value": 5900},
            {"key": "drop_in_fee_cents", "value": 2500},
            {"key": "court_monthly_cents", "value": 0},
            {"key": "initial_cash_cents", "value": 24500},
            {"key": "billing_day", "value": 1},
            {"key": "monthly_due_day", "value": 15},
            {"key": "pix_key", "value": ""},
        ],
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("expenses")
    op.drop_index("ix_payments_charge_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_charges_player_id", table_name="charges")
    op.drop_table("charges")
    op.drop_index("ix_attendances_player_id", table_name="attendances")
    op.drop_index("ix_attendances_game_id", table_name="attendances")
    op.drop_table("attendances")
    op.drop_table("games")
    op.drop_table("players")
    op.drop_table("users")
