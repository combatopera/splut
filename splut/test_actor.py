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

from .actor import Spawn
from concurrent.futures import ThreadPoolExecutor
from diapyr.util import invokeall
from unittest import TestCase

class Sum:

    s = 0

    def plus(self, x):
        self.s += x
        return self.s

class Network:

    def download(self, url):
        return url * 2

class Encoder:

    def __init__(self, networkactor):
        self.networkactor = networkactor

    async def encoded(self):
        return await self.networkactor.download('bar') + 'baz'

class TestSpawn(TestCase):

    def setUp(self):
        self.e = ThreadPoolExecutor()
        self.spawn = Spawn(self.e)

    def tearDown(self):
        self.e.shutdown()

    def test_works(self):
        sumactor = self.spawn(Sum())
        self.assertEqual('SumActor', type(sumactor).__name__)
        f = sumactor.plus(5)
        g = sumactor.plus(2)
        self.assertEqual(5, f.wait())
        self.assertEqual(7, g.wait())

    def test_suspend(self):
        self.assertEqual('barbarbaz', self.spawn(Encoder(self.spawn(Network()))).encoded().wait())

    def test_suspendthis(self):
        class Obj:
            def priv(self):
                return 100
            async def api(self):
                return await actor.priv()
        actor = self.spawn(Obj())
        self.assertEqual(100, actor.api().wait())

    def test_catch(self):
        class X(Exception):
            pass
        class A:
            def x(self):
                raise X
        class C:
            def __init__(self, a):
                self.a = a
            async def foo(self):
                try:
                    await self.a.x()
                except X:
                    return 100
        self.assertEqual(100, self.spawn(C(self.spawn(A()))).foo().wait())

    def test_sharedmailbox(self):
        sums = [Sum() for _ in range(5)]
        a = self.spawn(*sums)
        invokeall([a.plus(1).wait for _ in range(100)])
        self.assertEqual(100, sum(s.s for s in sums))

    def test_asymmetricworkers(self):
        class X:
            def x(self):
                return 100
        class Y:
            def y(self):
                return 200
        a = self.spawn(X(), Y())
        self.assertEqual('XYActor', type(a).__name__)
        g = a.y() # Skip unsuitable worker.
        f = a.x()
        self.assertEqual(100, f.wait())
        self.assertEqual(200, g.wait())

    def test_corofail(self):
        class X(Exception):
            pass
        class A:
            def foo(self):
                pass
        class B:
            async def x(self, a):
                await a.foo()
                raise X
        f = self.spawn(B()).x(self.spawn(A()))
        with self.assertRaises(X):
            f.wait()
