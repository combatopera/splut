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

    n = 0

    def plus(self, k):
        self.n += k
        return self.n

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
        x = X()
        class Thrower:
            def x(self):
                raise x
            def y(self):
                return 200
        class Obj:
            def __init__(self, a):
                self.a = a
            async def foo(self):
                try:
                    await self.a.x()
                except Exception as e:
                    return e
            async def foo2(self):
                try:
                    await self.a.x()
                except X:
                    return await self.a.y()
        a = self.spawn(Obj(self.spawn(Thrower())))
        self.assertIs(x, a.foo().wait())
        self.assertEqual(200, a.foo2().wait())

    def test_sharedmailbox(self):
        sums = [Sum() for _ in range(5)]
        invokeall([a.plus(1).wait for a in [self.spawn(*sums)] for _ in range(100)])
        self.assertEqual(100, sum(s.n for s in sums))

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
        class Q:
            def foo(self):
                pass
        class T:
            async def x(self, a):
                await a.foo()
                raise X
        f = self.spawn(T()).x(self.spawn(Q()))
        with self.assertRaises(X):
            f.wait()

    def test_badawaitable(self):
        from asyncio import sleep
        class Obj:
            async def m(self):
                return await sleep(5)
        w = self.spawn(Obj()).m().wait
        with self.assertRaises(RuntimeError):
            w()

    def test_badawaitable2(self):
        from asyncio import Future
        g = Future()
        class Obj:
            async def m(self):
                return await g
        w = self.spawn(Obj()).m().wait
        with self.assertRaises(RuntimeError) as cm:
            w()
        self.assertEqual((f"Unusable yield: {g}",), cm.exception.args)

    def test_badawaitable3(self):
        class Obj:
            async def m(self):
                return await 100
        w = self.spawn(Obj()).m().wait
        with self.assertRaises(TypeError):
            w()
