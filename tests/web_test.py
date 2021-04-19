"""
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
"""

import pytest

from libup import model, web


@pytest.fixture
def client():
    web.app.config['TESTING'] = True
    # Use in-memory database
    web.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    # Create all the tables
    model.Base.metadata.create_all(web.db.engine)
    # Seed some data
    web.db.session.add(model.Repository(name='test/errors', branch='master', is_error=True))
    web.db.session.add(model.Repository(name='test/ok', branch='master', is_error=False))
    # repo_id=2 --> test/ok
    log = model.Log(repo_id=2, time='20210419042355', is_error=True)
    log.set_text("foobarbaz")
    web.db.session.add(log)

    with web.app.test_client() as client:
        yield client


def test_index(client):
    rv = client.get('/')
    assert 'LibUp (aka libraryupgrader)' in rv.data.decode()


def test_errors(client):
    rv = client.get('/errors')
    assert 'test/errors' in rv.data.decode()
    assert 'test/ok' not in rv.data.decode()


def test_r(client):
    rv = client.get('/r/test/ok')
    assert 'test/ok' in rv.data.decode()
    # URL link to log #1
    assert '/logs2/1"' in rv.data.decode()
    rv = client.get('/r/test/does-not-exist')
    assert 'Sorry, I don\'t know this repository' in rv.data.decode()


def test_r_index(client):
    rv = client.get('/r')
    assert 'test/ok' in rv.data.decode()
    assert 'test/errors' in rv.data.decode()


def test_credits_(client):
    rv = client.get('/credits')
    assert 'thank you' in rv.data.decode()
