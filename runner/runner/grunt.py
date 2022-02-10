"""
Copyright (C) 2019 Kunal Mehta <legoktm@debian.org>

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
import os
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
                text += f'{indent}{key}: {exp}'
                if count != len(data):
                    # Last item gets a comma
                    text += ','
                text += '\n'
            text += indent[:-1] + '}'
            return text
        elif isinstance(data, bool):
            return 'true' if data else 'false'
        elif isinstance(data, str):
            if data == '!!GRUNT FIX!!':
                return "grunt.option( 'fix' )"
            elif data.startswith('COMMENT:'):
                return "// " + data.split(':', 1)[1].strip()
            return "'%s'" % data
        elif isinstance(data, int):
            return str(data)
        elif isinstance(data, list):
            if len(data) == 1:
                return "[ '%s' ]" % data[0]
            elif len(data) == 2:
                ret = "[ '{}', '{}' ]".format(data[0], data[1])
                if len(ret) < 25:
                    return ret
                # else fallthrough for a normal list
            text = '[\n'
            for index, item in enumerate(data):
                exp = self._export(item, indent + '\t')
                text += indent + exp
                if index + 1 != len(data) and not exp.startswith('//'):
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

    def get_file_list(self, section: str):
        """do not use this with set_section"""
        data = self.parse_section(section)
        gf_key = 'all' if 'all' in data else 'src'
        if not isinstance(data[gf_key], list):
            # It's a str
            data[gf_key] = [data[gf_key]]
        return [x for x in data[gf_key] if not x.startswith('COMMENT:')]

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
        elif inp == "grunt.option( 'fix' )":
            inp = '"!!GRUNT FIX!!"'
        return inp

    def _fixup_lines(self, lines: list) -> list:
        new = []
        for item in lines:
            item = item.strip()
            if item.lstrip().startswith('//'):
                new.append('"' + item.replace('//', 'COMMENT:') + '",')
            else:
                new.append(item)
        return new

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
                before_match = re.search(r'(\t+?)\S', line)
                if before_match:
                    before = before_match.group(1)
                else:
                    raise RuntimeError("Cannot find before")
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
                before_match = re.search(r'(\t+?)\S', line)
                if before_match:
                    before = before_match.group(1)
                else:
                    raise RuntimeError("Cannot find before")
                for subindex, subline in enumerate(lines[index:]):
                    if subline.startswith(before + ']'):
                        break
                else:
                    raise RuntimeError('???')
                # OK, we're going to assume that it's just a plain list. No nested structures.
                # Please.
                key = line.split(':', 1)[0].strip()
                listy = '[' + '\n'.join(self._fixup_lines(lines[index + 1:index + subindex])) + ']'
                data[key] = ast.literal_eval(listy)
                skip_to = index + subindex + 1
                continue
            elif ':' in line:
                key, val = line.split(':', 1)
                data[key.strip()] = ast.literal_eval(self._normalize(val.strip()))
            elif not line.strip():
                continue
            else:
                print(line)
                raise RuntimeError

        return data

    def _find_tasks(self):
        return re.search(r"registerTask\(\s*?'(lint|test)',\s*?\[\s*?(.*?)\s*?\]\s*?\);", self.text, flags=re.DOTALL)

    def tasks(self) -> list:
        return ast.literal_eval('[' + self._find_tasks().group(2) + ']')

    def set_tasks(self, new_tasks: list):
        self.text = self.text.replace(self._find_tasks().group(2), ' ' + str(new_tasks)[1:-1])


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
            if not search:
                raise RuntimeError("Cannot find {...}")
            for part in search.group(1).split(','):
                new = path.replace(search.group(0), part, 1)
                paths.append(new)
            paths.remove(path)

    return paths


def expand_glob(paths: list) -> list:
    """see https://gruntjs.com/api/grunt.file#grunt.file.expand"""
    include = []
    exclude = ['node_modules/**', 'vendor/**']
    for path in paths:
        # We need to implement leading ! as exclude
        if path.startswith('!'):
            exclude.extend(expand_braces(path[1:]))
        else:
            include.extend(expand_braces(path))
    include_paths = set()
    # Always ignore files under node_modules/ and vendor/
    exclude_paths = set()
    for ipath in include:
        include_paths.update(set(glob.iglob(ipath, recursive=True)))
    for epath in exclude:
        exclude_paths.update(set(glob.iglob(epath, recursive=True)))

    return [path for path in include_paths if path not in exclude_paths]


def __check_everything():
    files = glob.glob(os.path.expanduser('~/gerrit/mediawiki/core/extensions/*/Gruntfile.js'))
    for fname in sorted(files):
        if '/Popups/' in fname:
            # Whatever.
            continue
        gf = Gruntfile(fname)
        if 'grunt-eslint' in gf.text:
            print(fname)
            print(gf.tasks())
            original = gf.text
            data = gf.parse_section('eslint')
            assert data.get('all') or data.get('shared') or data.get('target') or data.get('src')
            gf.set_section('eslint', data)
            if gf.text != original:
                print('\n'.join(difflib.Differ().compare(original.splitlines(), gf.text.splitlines())))
                break


if __name__ == '__main__':
    __check_everything()
