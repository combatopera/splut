# Copyright 2014, 2018 Andrzej Cichocki

# This file is part of pym2149.
#
# pym2149 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pym2149 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pym2149.  If not, see <http://www.gnu.org/licenses/>.

import re, logging, os, importlib

log = logging.getLogger(__name__)

class Expression:

    def __init__(self, head, code, name):
        self.head = head
        self.code = code
        self.name = name

    def run(self, g):
        exec (self.head, g)
        exec (self.code, g)
        return g

    def resolve(self, view):
        return self.run({'config': view})[self.name]

    def modify(self, view, objname, obj):
        self.run({'config': view, objname: obj})

class Expressions:

    # TODO LATER: Ideally inspect the AST as this can give false positives.
    toplevelassignment = re.compile(r'^([^\s]+)\s*=')
    fromimport = re.compile(r'^from\s')

    @staticmethod
    def canonicalize(path):
        while True:
            try:
                link = os.readlink(path)
            except OSError:
                return path
            path = os.path.join(os.path.dirname(path), link)

    def __init__(self):
        self.expressions = {}

    def loadmodule(self, package, name):
        self.loadpath(importlib.util.find_spec(name, package).origin)

    def loadpath(self, path):
        f = open(path)
        try:
            self.loadlines(path, f.readline)
        finally:
            f.close()

    def loadlines(self, path, readline):
        head0 = []
        head1 = [
            "__file__ = %r\n" % self.canonicalize(path),
            'def sys_path_add(path):\n',
            '    import sys\n',
            '    if path not in sys.path:\n',
            '        sys.path.append(path)\n',
        ]
        line = readline()
        while line and self.toplevelassignment.search(line) is None:
            (head1 if self.fromimport.search(line) is None else head0).append(line)
            line = readline()
        tocode = lambda block: compile(block, '<string>', 'exec')
        head = head0 + head1
        log.debug("[%s] Header is first %s lines.", path, len(head))
        head = tocode(''.join(head))
        while line:
            m = self.toplevelassignment.search(line)
            if m is not None:
                name = m.group(1)
                self.expressions[name] = Expression(head, tocode(line), name)
            line = readline()

    def expression(self, name):
        return self.expressions[name]

    def modifiers(self, name):
        for e in self.expressions.values():
            if e.name.startswith(name + '['):
                yield e
