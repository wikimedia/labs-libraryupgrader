"""
Add flag fields to repositories

Copyright (C) 2020 Kunal Mehta <legoktm@debian.org>

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

Revision ID: f0c31ad3074e
Revises: 714526ec1c10
Create Date: 2020-12-28 12:19:48.687591
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0c31ad3074e'
down_revision = '714526ec1c10'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('repositories', sa.Column('is_bundled', sa.Boolean(), nullable=False))
    op.add_column('repositories', sa.Column('is_canary', sa.Boolean(), nullable=False))
    op.add_column('repositories', sa.Column('is_wm_deployed', sa.Boolean(), nullable=False))


def downgrade():
    op.drop_column('repositories', 'is_wm_deployed')
    op.drop_column('repositories', 'is_canary')
    op.drop_column('repositories', 'is_bundled')
