"""
Add upstreams table

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

Revision ID: 136ea9422629
Revises: d068e96fb459
Create Date: 2020-12-26 01:11:34.274956
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '136ea9422629'
down_revision = 'd068e96fb459'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'upstreams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('manager', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.BLOB(), nullable=False),
        sa.Column('latest', sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('upstreams')
