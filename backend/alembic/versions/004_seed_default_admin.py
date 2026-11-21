"""Former default admin seed, kept empty so existing databases keep a valid revision chain

The admin account is now created on API startup from ADMIN_LOGIN / ADMIN_PASSWORD.

Revision ID: 004_seed_default_admin
Revises: 003_add_users_table
Create Date: 2026-11-20

"""
from typing import Sequence, Union

revision: str = '004_seed_default_admin'
down_revision: Union[str, None] = '003_add_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
