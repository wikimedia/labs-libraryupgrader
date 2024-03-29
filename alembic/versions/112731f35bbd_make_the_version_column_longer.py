"""
Make the version column longer

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

Revision ID: 112731f35bbd
Revises: 36130068b5f9
Create Date: 2020-12-22 16:51:57.392145
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '112731f35bbd'
down_revision = '36130068b5f9'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'dependencies', 'version',
        existing_type=mysql.VARCHAR(length=50),
        type_=sa.String(length=150),
        existing_nullable=False
    )


def downgrade():
    op.alter_column(
        'dependencies', 'version',
        existing_type=sa.String(length=150),
        type_=mysql.VARCHAR(length=50),
        existing_nullable=False
    )
