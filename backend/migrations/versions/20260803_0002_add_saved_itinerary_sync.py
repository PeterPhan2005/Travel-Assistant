"""Add complete saved-itinerary snapshots, revisions, and tombstones.

Revision ID: 20260803_0002
Revises: 20260727_0001
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260803_0002"
down_revision: str | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend the T030 itinerary tables without replacing them."""
    op.add_column(
        "itineraries",
        sa.Column(
            "revision",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "city",
            sa.String(length=16),
            server_default=sa.text("'hcmc'"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "local_date",
            sa.Date(),
            server_default=sa.text("DATE '1970-01-01'"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'Asia/Ho_Chi_Minh'"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "start_local_time",
            sa.Time(timezone=False),
            server_default=sa.text("TIME '00:00:00'"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "end_local_time",
            sa.Time(timezone=False),
            server_default=sa.text("TIME '23:59:00'"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "assumptions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_itineraries_revision_positive",
        "itineraries",
        "revision > 0",
    )
    op.create_check_constraint(
        "ck_itineraries_city_supported",
        "itineraries",
        "city IN ('hcmc', 'bkk')",
    )
    op.create_check_constraint(
        "ck_itineraries_city_timezone_consistent",
        "itineraries",
        "(city = 'hcmc' AND timezone = 'Asia/Ho_Chi_Minh') OR "
        "(city = 'bkk' AND timezone = 'Asia/Bangkok')",
    )
    op.create_check_constraint(
        "ck_itineraries_local_time_order",
        "itineraries",
        "start_local_time < end_local_time",
    )
    op.create_check_constraint(
        "ck_itineraries_assumptions_array",
        "itineraries",
        "jsonb_typeof(assumptions) = 'array'",
    )
    op.create_check_constraint(
        "ck_itineraries_warnings_array",
        "itineraries",
        "jsonb_typeof(warnings) = 'array'",
    )

    op.create_table(
        "itinerary_tombstones",
        sa.Column("itinerary_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision > 0",
            name="ck_itinerary_tombstones_revision_positive",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_itinerary_tombstones_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "itinerary_id",
            name="pk_itinerary_tombstones",
        ),
    )
    op.create_index(
        "ix_itinerary_tombstones_user_id",
        "itinerary_tombstones",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove T071-only revision and snapshot fields."""
    op.drop_index(
        "ix_itinerary_tombstones_user_id",
        table_name="itinerary_tombstones",
    )
    op.drop_table("itinerary_tombstones")
    op.drop_constraint(
        "ck_itineraries_warnings_array",
        "itineraries",
        type_="check",
    )
    op.drop_constraint(
        "ck_itineraries_assumptions_array",
        "itineraries",
        type_="check",
    )
    op.drop_constraint(
        "ck_itineraries_local_time_order",
        "itineraries",
        type_="check",
    )
    op.drop_constraint(
        "ck_itineraries_city_timezone_consistent",
        "itineraries",
        type_="check",
    )
    op.drop_constraint(
        "ck_itineraries_city_supported",
        "itineraries",
        type_="check",
    )
    op.drop_constraint(
        "ck_itineraries_revision_positive",
        "itineraries",
        type_="check",
    )
    op.drop_column("itineraries", "warnings")
    op.drop_column("itineraries", "assumptions")
    op.drop_column("itineraries", "end_local_time")
    op.drop_column("itineraries", "start_local_time")
    op.drop_column("itineraries", "timezone")
    op.drop_column("itineraries", "local_date")
    op.drop_column("itineraries", "city")
    op.drop_column("itineraries", "revision")
