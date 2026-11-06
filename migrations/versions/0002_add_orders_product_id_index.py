"""add index on orders.product_id

Индекс под частый запрос: GET /api/products/{id}/orders и статистика (JOIN по product_id).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 10:30:00

"""
from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_orders_product_id"), ["product_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_orders_product_id"))
