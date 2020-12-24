"""
Make dependencies.manager non-nullable

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

Revision ID: a2452f842414
Revises: 23223bb47663
Create Date: 2020-12-23 22:12:35.889748
"""

from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a2452f842414'
down_revision = '23223bb47663'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'dependencies', 'manager',
        existing_type=mysql.VARCHAR(length=20),
        nullable=False
    )


def downgrade():
    op.alter_column(
        'dependencies', 'manager',
        existing_type=mysql.VARCHAR(length=20),
        nullable=True
    )
