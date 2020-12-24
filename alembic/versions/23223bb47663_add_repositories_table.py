"""
Add repositories table

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

Revision ID: 23223bb47663
Revises: 112731f35bbd
Create Date: 2020-12-23 21:57:03.634770
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '23223bb47663'
down_revision = '112731f35bbd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('branch', sa.String(length=50), nullable=False),
        sa.Column('is_error', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('repositories')
