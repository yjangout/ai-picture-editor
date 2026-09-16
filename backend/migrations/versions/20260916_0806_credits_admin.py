"""credits admin

Revision ID: c8e4a1d92b70
Revises: fa850313b768
"""

import sqlalchemy as sa
from alembic import op

revision = "c8e4a1d92b70"
down_revision = "fa850313b768"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=16), server_default="user", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("credits", sa.Integer(), server_default="100", nullable=False),
    )
    op.add_column(
        "tool_runs",
        sa.Column("credits_charged", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("ref_type", sa.String(length=32), nullable=True),
        sa.Column("ref_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_credit_ledger_user_id"), "credit_ledger", ["user_id"])
    op.execute(
        """
        INSERT INTO credit_ledger (id, user_id, amount, balance_after, kind, reason, created_at)
        SELECT gen_random_uuid(), id, credits, credits, 'signup', '注册赠送', created_at
        FROM users
        WHERE credits > 0
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_credit_ledger_user_id"), table_name="credit_ledger")
    op.drop_table("credit_ledger")
    op.drop_column("tool_runs", "credits_charged")
    op.drop_column("users", "credits")
    op.drop_column("users", "role")
