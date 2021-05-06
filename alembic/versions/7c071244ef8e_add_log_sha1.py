"""
add log.sha1

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

Revision ID: 7c071244ef8e
Revises: 3ddcb00cd72a
Create Date: 2021-05-06 16:19:50.221255
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c071244ef8e'
down_revision = '3ddcb00cd72a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('logs', sa.Column('sha1', sa.String(length=40), nullable=True))


def downgrade():
    op.drop_column('logs', 'sha1')
