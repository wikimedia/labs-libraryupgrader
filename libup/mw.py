#!/usr/bin/env python3
"""
Common functions for MediaWiki stuff things.
Copyright (C) 2017-2018 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import wikimediaci_utils as ci

from . import gerrit


# Gerrit repos not under mediawiki/libs/
OTHER_LIBRARIES = [
    'AhoCorasick',
    'CLDRPluralRuleParser',
    'HtmlFormatter',
    'IPSet',
    'RelPath',
    'RunningStat',
    'VisualEditor/VisualEditor',
    'WrappedString',
    'at-ease',
    'base-convert',
    'cdb',
    'css-sanitizer',
    'data-values/value-view',
    'integration/docroot',
    'labs/tools/coverme',
    'labs/tools/stewardbots',
    'mediawiki/oauthclient-php',
    'mediawiki/services/parsoid',
    'mediawiki/tools/codesniffer',
    'mediawiki/tools/minus-x',
    'mediawiki/tools/phan',
    'mediawiki/tools/phan/SecurityCheckPlugin',
    'mediawiki/tools/phpunit-patch-coverage',
    'oojs/core',
    'oojs/ui',
    'php-session-serializer',
    'purtle',
    'testing-access-wrapper',
    'translatewiki',
    'unicodejs',
    'utfnormal',
    'wikibase/javascript-api',
    'wikimedia/lucene-explain-parser',
    'wikimedia/portals',
    'wikimedia/textcat',
]


def get_everything():
    yield from sorted(ci.mw_things_repos())
    yield from sorted(get_library_list())


def get_library_list():
    yield from gerrit.list_projects('mediawiki/libs/')
    yield from OTHER_LIBRARIES
