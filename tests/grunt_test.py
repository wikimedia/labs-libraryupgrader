"""
Copyright (C) 2019 Kunal Mehta <legoktm@member.fsf.org>

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

from libup import grunt


def test_gruntfile(tempfs):
    original = tempfs.fixture('grunt', 'Gruntfile.js')
    tempfs.create_file('Gruntfile.js',
                       contents=original)
    gf = grunt.Gruntfile()
    eslint = gf.parse_section('eslint')
    assert eslint == {
        'all': '.',
        'options': {
            'cache': True,
            'reportUnusedDisableDirectives': True,
        }
    }
    stylelint = gf.parse_section('stylelint')
    assert stylelint == {
        'all': ['**/*.css', '!node_modules/**', '!vendor/**'],
    }
    tasks = gf.tasks()
    assert tasks == ['jsonlint', 'banana', 'eslint', 'stylelint']
    # Rebuild/roundtrip
    gf.set_section('eslint', eslint)
    gf.set_section('stylelint', stylelint)
    gf.set_tasks(tasks)
    assert original == gf.text
    with pytest.raises(grunt.NoSuchSection):
        gf.parse_section('doesnotexist')


def test_remove_section(tempfs):
    tempfs.create_file('Gruntfile.js',
                       contents=tempfs.fixture('grunt', 'Gruntfile.js'))
    gf = grunt.Gruntfile()
    gf.remove_section('jsonlint')
    tasks = gf.tasks()
    tasks.remove('jsonlint')
    gf.set_tasks(tasks)
    assert tempfs.fixture('grunt', 'Gruntfile.js-no-jsonlint') == gf.text


def test_expand_braces():
    assert [
        'vendor/foo.js',
        'vendor/foo.json',
        'node_modules/foo.js',
        'node_modules/foo.json',
    ] == grunt.expand_braces('{node_modules,vendor}/foo.js{,on}')


def test_expand_glob(tempfs):
    paths = [
        'foo.js',
        'foo.json',
        'i18n/foo.json',
        'resources/foo.js',
        'node_modules/foo.js',
        'vendor/foo.json',
    ]
    for path in paths:
        tempfs.create_file(path, contents='')
    actual = grunt.expand_glob([
        '**/*.js{,on}',
        '!{node_modules,vendor}/**',
    ])
    assert ['foo.js', 'foo.json', 'i18n/foo.json', 'resources/foo.js'] \
        == sorted(actual)
