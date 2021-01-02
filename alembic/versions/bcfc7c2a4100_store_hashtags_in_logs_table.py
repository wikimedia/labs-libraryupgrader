"""
Store hashtags in logs table

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

Revision ID: bcfc7c2a4100
Revises: f0c31ad3074e
Create Date: 2021-01-01 16:02:38.727799
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcfc7c2a4100'
down_revision = 'f0c31ad3074e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('logs', sa.Column('hashtags', sa.BLOB(), nullable=True))


def downgrade():
    op.drop_column('logs', 'hashtags')
