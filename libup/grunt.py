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

import ast
from collections import OrderedDict
import difflib
import glob
import json
import re


class NoSuchSection(Exception):
    pass


class Gruntfile:
    """a just-good-enough parser of Gruntfile.js"""
    def __init__(self, fname='Gruntfile.js'):
        self.fname = fname
        with open(self.fname) as f:
            self.text = f.read()
        self.has_comma = {}

    def save(self):
        with open(self.fname, 'w') as f:
            f.write(self.text)

    def set_section(self, section, data: dict):
        text = self._export({section: data}, '\t\t')
        sp = text.splitlines()
        final = '\n'.join(sp[1:-1]) + self.has_comma[section]
        self.text = self.text.replace(self._find(section).group(0), final)

    def _export(self, data, indent: str) -> str:
        text = ''
        if isinstance(data, dict):
            text += '{\n'
            count = 0
            for key, val in data.items():
                count += 1
                exp = self._export(val, indent + '\t')
                text += '%s%s: %s' % (indent, key, exp)
                if count != len(data):
                    # Last item gets a comma
                    text += ','
                text += '\n'
            text += indent[:-1] + '}'
            return text
        elif isinstance(data, bool):
            return 'true' if data else 'false'
        elif isinstance(data, str):
            return "'%s'" % data
        elif isinstance(data, list):
            if len(data) == 1:
                return "[ '%s' ]" % data[0]
            elif len(data) == 2:
                ret = "[ '%s', '%s' ]" % (data[0], data[1])
                if len(ret) < 25:
                    return ret
                # else fallthrough for a normal list
            text = '[\n'
            for index, item in enumerate(data):
                text += indent + self._export(item, indent + '\t')
                if index + 1 != len(data):
                    text += ','
                text += '\n'
            text += indent[:-1] + ']'
            return text
        else:
            raise RuntimeError('unknown type')

    def _find(self, section):
        found = re.search(
            r'\t\t%s: {(.*?)\n\t\t}(,|\n\t})' % section,
            self.text,
            flags=re.MULTILINE | re.DOTALL
        )
        if not found:
            raise NoSuchSection
        return found

    def parse_section(self, section: str) -> OrderedDict:
        base = self._find(section)
        self.has_comma[section] = base.group(2)
        return self._inner_parse(base.group(1).splitlines()[1:])

    def remove_section(self, section: str):
        self.text = self.text.replace('\n' + self._find(section).group(0), '')
        self.text = self.text.replace(
            "\tgrunt.loadNpmTasks( 'grunt-%s' );\n" % section, ''
        )

    def _normalize(self, inp: str) -> str:
        if inp.endswith(','):
            inp = inp[:-1]
        if inp == 'true':
            inp = 'True'
        elif inp == 'false':
            inp = 'False'
        return inp

    def _inner_parse(self, lines: list) -> OrderedDict:
        data = OrderedDict()
        skip_to = 0
        for index, line in enumerate(lines):
            if skip_to > index:
                continue
            # print('%s: %s' %(index, line))
            # We remove all text strings so e.g. foo: '{baz,bar}/buz' doesn't trip
            cleaned_line = re.sub(r"'(.*?)'", '', line)
            if '{' in cleaned_line:
                # Find the closing line by indentation
                before = re.search(r'(\t+?)\S', line).group(1)
                for subindex, subline in enumerate(lines[index:]):
                    # print('%s: ' % subindex + repr(subline))
                    if subline.startswith(before + '}'):
                        break
                else:
                    raise RuntimeError('???')
                key = line.split(':', 1)[0].strip()
                data[key] = self._inner_parse(lines[index + 1:index + subindex])
                skip_to = index + subindex + 1
                continue
            elif '[' in cleaned_line and ']' not in cleaned_line:
                # Find the closing line by indentation
                before = re.search(r'(\t+?)\S', line).group(1)
                for subindex, subline in enumerate(lines[index:]):
                    if subline.startswith(before + ']'):
                        break
                else:
                    raise RuntimeError('???')
                # OK, we're going to assume that it's just a plain list. No nested structures.
                # Please.
                key = line.split(':', 1)[0].strip()
                listy = '[' + '\n'.join(lines[index + 1:index + subindex]) + ']'
                data[key] = ast.literal_eval(listy)
                skip_to = index + subindex + 1
                continue
            elif ':' in line:
                key, val = line.split(':', 1)
                data[key.strip()] = ast.literal_eval(self._normalize(val.strip()))
            else:
                # print(line)
                raise RuntimeError

        return data

    def _find_tasks(self):
        return re.search(r"registerTask\( '(lint|test)', \[ (.*?) \] \);", self.text)

    def tasks(self) -> list:
        return ast.literal_eval('[' + self._find_tasks().group(2) + ']')

    def set_tasks(self, new_tasks: list):
        self.text = self.text.replace(self._find_tasks().group(2), str(new_tasks)[1:-1])


def expand_braces(path: str) -> list:
    """
    fnmatch/glob doesn't support .js{,on} style globbing,
    so we need to reimplement it!

    see https://bugs.python.org/issue9584
    """
    paths = [path]
    while any(['{' in path for path in paths]):
        for path in paths:
            if '{' not in path:
                continue
            search = re.search('{(.*?)}', path)
            for part in search.group(1).split(','):
                new = path.replace(search.group(0), part, 1)
                paths.append(new)
            paths.remove(path)

    return paths


def expand_glob(paths: list) -> list:
    """see https://gruntjs.com/api/grunt.file#grunt.file.expand"""
    include = []
    exclude = []
    for path in paths:
        # We need to implement leading ! as exclude
        if path.startswith('!'):
            exclude.extend(expand_braces(path[1:]))
        else:
            include.extend(expand_braces(path))
    include_paths = set()
    exclude_paths = set()
    for ipath in include:
        include_paths.update(set(glob.iglob(ipath, recursive=True)))
    for epath in exclude:
        exclude_paths.update(set(glob.iglob(epath, recursive=True)))

    return [path for path in include_paths if path not in exclude_paths]


def __check_everything():
    files = glob.glob('/home/km/gerrit/mediawiki/core/extensions/*/Gruntfile.js')
    for fname in sorted(files):
        if '/Popups/' in fname:
            # Whatever.
            continue
        gf = Gruntfile(fname)
        if 'grunt-eslint' in gf.text:
            print(fname)
            gf.tasks()
            original = gf.text
            data = gf.parse_section('eslint')
            assert data.get('all') or data.get('shared')
            print(json.dumps(data))
            gf.set_section('eslint', data)
            if gf.text != original:
                print('\n'.join(difflib.Differ().compare(original.splitlines(), gf.text.splitlines())))
                break


if __name__ == '__main__':
    __check_everything()
