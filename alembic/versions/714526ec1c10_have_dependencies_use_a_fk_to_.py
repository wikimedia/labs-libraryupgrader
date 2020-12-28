"""
Have dependencies use a fk to repositories

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

Revision ID: 714526ec1c10
Revises: 34610d904101
Create Date: 2020-12-27 17:01:46.382289
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '714526ec1c10'
down_revision = '34610d904101'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dependencies', sa.Column('repo_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'dependencies', 'repositories', ['repo_id'], ['id'])
    op.drop_column('dependencies', 'repo')
    op.drop_column('dependencies', 'branch')


def downgrade():
    op.add_column('dependencies', sa.Column('branch', mysql.VARCHAR(length=30), nullable=False))
    op.add_column('dependencies', sa.Column('repo', mysql.VARCHAR(length=150), nullable=False))
    op.drop_constraint(None, 'dependencies', type_='foreignkey')
    op.drop_column('dependencies', 'repo_id')
