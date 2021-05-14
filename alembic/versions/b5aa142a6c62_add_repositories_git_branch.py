"""
add repositories.git_branch

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

Revision ID: b5aa142a6c62
Revises: 7c071244ef8e
Create Date: 2021-05-13 22:41:20.591730
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5aa142a6c62'
down_revision = '7c071244ef8e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('repositories', sa.Column('git_branch', sa.String(length=80), nullable=True))


def downgrade():
    op.drop_column('repositories', 'git_branch')
