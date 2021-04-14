"""
add monitoring table

Copyright (C) 2021 Kunal Mehta <legoktm@debian.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Revision ID: 3ddcb00cd72a
Revises: 0105e6b69847
Create Date: 2021-04-14 02:29:35.816669
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ddcb00cd72a'
down_revision = '0105e6b69847'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'monitoring',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=30), nullable=False),
        sa.Column('version', sa.String(length=80), nullable=True),
        sa.Column('task', sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('monitoring')
