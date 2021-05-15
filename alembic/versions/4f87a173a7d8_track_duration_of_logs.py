"""
track duration of logs

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

Revision ID: 4f87a173a7d8
Revises: b5aa142a6c62
Create Date: 2021-05-15 05:06:59.546944
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f87a173a7d8'
down_revision = 'b5aa142a6c62'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('logs', sa.Column('duration', sa.Integer(), nullable=False))


def downgrade():
    op.drop_column('logs', 'duration')
