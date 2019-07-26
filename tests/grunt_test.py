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

from libup import grunt

# This variable is indented with spaces to please flake8, but replaced
# at the very bottom. Sigh.
GRUNTFILE = """/* eslint-env node */
module.exports = function ( grunt ) {
    grunt.loadNpmTasks( 'grunt-jsonlint' );
    grunt.loadNpmTasks( 'grunt-eslint' );
    grunt.loadNpmTasks( 'grunt-banana-checker' );
    grunt.loadNpmTasks( 'grunt-stylelint' );

    grunt.initConfig( {
        banana: {
            all: [
                'i18n/'
            ]
        },
        eslint: {
            all: '.',
            options: {
                cache: true,
                reportUnusedDisableDirectives: true
            }
        },
        jsonlint: {
            all: [
                '**/*.json',
                '!node_modules/**',
                '!vendor/**'
            ]
        },
        stylelint: {
            all: [
                '**/*.css',
                '!node_modules/**',
                '!vendor/**'
            ]
        }
    } );

    grunt.registerTask( 'test', [ 'jsonlint', 'banana', 'eslint', 'stylelint' ] );
};
""".replace('    ', '\t')


def test_gruntfile(fs):
    fs.create_file('Gruntfile.js', contents=GRUNTFILE)
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
    # Rebuild/roundtrip
    gf.set_section('eslint', eslint)
    gf.set_section('stylelint', stylelint)
    assert gf.text == GRUNTFILE
