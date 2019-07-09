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

from .files import ComposerJson, PackageJson

pkg_json = """{
    "private": true,
    "scripts": {
        "test": "grunt test"
    },
    "devDependencies": {
        "eslint-config-wikimedia": "0.11.0",
        "grunt": "1.0.4",
        "grunt-banana-checker": "0.7.0"
    },
    "eslintIgnore": [
        "vendor/**"
    ]
}
"""

composer_json = """{
    "require-dev": {
        "jakub-onderka/php-parallel-lint": "1.0.0",
        "mediawiki/mediawiki-codesniffer": "25.0.0"
    },
    "extra": {
        "phan-taint-check-plugin": "1.5.0"
    }
}
"""


def test_package_json(fs):
    fs.create_file('package.json', contents=pkg_json)
    pkg = PackageJson('package.json')
    assert pkg.get_packages() == ['eslint-config-wikimedia', 'grunt', 'grunt-banana-checker']
    assert pkg.get_version('not-here') is None
    assert pkg.get_version('grunt') == '1.0.4'
    pkg.set_version('grunt', '1.0.5')
    assert pkg.get_version('grunt') == '1.0.5'
    with pytest.raises(RuntimeError):
        pkg.set_version('not-here', '0.0.0')
    # TODO: pkg.save()


def test_composer_json(fs):
    fs.create_file('composer.json', contents=composer_json)
    pkg = ComposerJson('composer.json')
    assert pkg.get_version('mediawiki/mediawiki-codesniffer') == '25.0.0'
    # p-t-c-p is in extra
    assert pkg.get_version('mediawiki/phan-taint-check-plugin') == '1.5.0'
    assert pkg.get_version('not-here') is None
    pkg.set_version('mediawiki/mediawiki-codesniffer', '26.0.0')
    pkg.set_version('mediawiki/phan-taint-check-plugin', '1.6.0')
    assert pkg.get_version('mediawiki/mediawiki-codesniffer') == '26.0.0'
    assert pkg.get_version('mediawiki/phan-taint-check-plugin') == '1.6.0'
    with pytest.raises(RuntimeError):
        pkg.set_version('not-here', '0.0.0')
    # TODO: pkg.save()
