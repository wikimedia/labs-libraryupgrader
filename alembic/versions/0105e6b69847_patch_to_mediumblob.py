"""
patch to mediumblob

Copyright (C) 2021 Kunal Mehta <legoktm@member.fsf.org>

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

Revision ID: 0105e6b69847
Revises: 1684256728e6
Create Date: 2021-04-06 17:51:31.384678
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0105e6b69847'
down_revision = '1684256728e6'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'logs', 'patch',
        existing_type=sa.BLOB(),
        type_=sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), 'mysql'),
        existing_nullable=True
    )


def downgrade():
    op.alter_column(
        'logs', 'patch',
        existing_type=sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), 'mysql'),
        type_=sa.BLOB(),
        existing_nullable=True
    )
