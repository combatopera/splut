# Copyright 2014, 2018, 2019, 2020 Andrzej Cichocki

# This file is part of splut.
#
# splut is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# splut is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with splut.  If not, see <http://www.gnu.org/licenses/>.

from . import Spawn
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from diapyr.util import invokeall
from lagoon import tee
from lagoon.program import partial
from lagoon.util import onerror
from pathlib import Path
from shutil import copytree, rmtree
from subprocess import DEVNULL
from tempfile import mkdtemp
from threading import Semaphore
from unittest import TestCase

class Worker:

    def __init__(self, template):
        self.busy = Semaphore()
        self.tempdir = mkdtemp()
        with onerror(self.dispose):
            copy = Path(self.tempdir, 'copy')
            copytree(template, copy)
            self.state = copy / 'state'
            self.tee = tee._a[partial](self.state, stdout = DEVNULL)

    def read(self):
        return self.state.read_text()

    def dispose(self):
        rmtree(self.tempdir)

    @contextmanager
    def _check(self):
        assert self.busy.acquire(False)
        try:
            yield
        finally:
            self.busy.release()

    def typea(self, arg):
        with self._check():
            self.tee(input = f"A {arg}\n")

    def typeb(self, arg):
        with self._check():
            self.tee(input = f"B {arg}\n")

    def typec(self, arg):
        with self._check():
            self.tee(input = f"C {arg}\n")

class TestWorkPool(TestCase):

    def setUp(self):
        self.workers = []
        self.masterdir = mkdtemp()
        with onerror(self.tearDown):
            Path(self.masterdir, 'state').write_text('HEAD\n')

    def tearDown(self):
        for w in self.workers:
            w.dispose()
        rmtree(self.masterdir)

    def test_works(self):
        for _ in range(5):
            self.workers.append(Worker(self.masterdir))
        with ThreadPoolExecutor() as e:
            invokeall([t(i).wait for a in [Spawn(e)(*self.workers)] for t in [a.typea, a.typeb, a.typec] for i in range(4)])
        self.assertEqual([
            'A 0', 'A 1', 'A 2', 'A 3',
            'B 0', 'B 1', 'B 2', 'B 3',
            'C 0', 'C 1', 'C 2', 'C 3',
        ], sorted(sum((w.read().splitlines()[1:] for w in self.workers), [])))
