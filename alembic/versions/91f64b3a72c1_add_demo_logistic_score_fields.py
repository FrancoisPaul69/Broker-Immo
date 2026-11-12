"""add DEMO logistic regression result fields to scores

Revision ID: 91f64b3a72c1
Revises: 7829421333dd
Create Date: 2026-11-10
"""

from alembic import op
import sqlalchemy as sa


revision = "91f64b3a72c1"
down_revision = "e45397ac4b71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scores", sa.Column("demo_logistic_probability", sa.Float(), nullable=True))
    op.add_column("scores", sa.Column("demo_logistic_training_label", sa.Boolean(), nullable=True))
    op.add_column("scores", sa.Column("demo_logistic_cv_folds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scores", "demo_logistic_cv_folds")
    op.drop_column("scores", "demo_logistic_training_label")
    op.drop_column("scores", "demo_logistic_probability")
