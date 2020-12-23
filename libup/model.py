"""
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
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Dependencies(Base):
    __tablename__ = "dependencies"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    version = Column(String(50), nullable=False)
    mode = Column(String(4), nullable=False)  # "prod" or "dev"
    repo = Column(String(150), nullable=False)  # TODO: normalize?
    branch = Column(String(30), nullable=False)  # TODO: normalize or combine with repo?
