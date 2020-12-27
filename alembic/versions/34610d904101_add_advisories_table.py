"""
Add advisories table

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

Revision ID: 34610d904101
Revises: 136ea9422629
Create Date: 2020-12-26 19:02:30.642316
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '34610d904101'
down_revision = '136ea9422629'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'advisories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo_id', sa.Integer(), nullable=True),
        sa.Column('manager', sa.String(length=10), nullable=False),
        sa.Column('data', sa.BLOB(), nullable=False),
        sa.ForeignKeyConstraint(['repo_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('advisories')
