"""
Added dependencies table

Copyright (C) 2020 Kunal Mehta <legoktm@member.fsf.org>

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

Revision ID: c741b11964b3
Revises:
Create Date: 2020-12-22 14:50:41.884246
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c741b11964b3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'dependencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('mode', sa.String(length=4), nullable=False),
        sa.Column('repo', sa.String(length=150), nullable=False),
        sa.Column('branch', sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('dependencies')
