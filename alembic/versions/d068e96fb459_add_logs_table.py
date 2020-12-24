"""
Add logs table

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

Revision ID: d068e96fb459
Revises: ea4834de64e9
Create Date: 2020-12-23 23:19:11.558789
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd068e96fb459'
down_revision = 'ea4834de64e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo_id', sa.Integer(), nullable=True),
        sa.Column('time', sa.String(length=15), nullable=False),
        sa.Column('text', sa.BLOB(), nullable=False),
        sa.Column('patch', sa.BLOB(), nullable=True),
        sa.Column('is_error', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['repo_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('logs')
