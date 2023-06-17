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

from .actor import Exchange
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

    async def foo(self):
        extra = 'baz'
        return await self.networkactor.download('bar') + extra

    def hmmm(self):
        return 100

    async def hmm(self):
        return await self.actor.hmmm()

class TestExchange(TestCase):

    def setUp(self):
        self.e = ThreadPoolExecutor()
        self.x = Exchange(self.e)

    def tearDown(self):
        self.e.shutdown()

    def test_works(self):
        sumactor = self.x.spawn(Sum())
        self.assertEqual('SumActor', type(sumactor).__name__)
        f = sumactor.plus(5)
        g = sumactor.plus(2)
        self.assertEqual(5, f.result())
        self.assertEqual(7, g.result())

    def test_suspend(self):
        networkactor = self.x.spawn(Network())
        encoderactor = self.x.spawn(Encoder(networkactor))
        self.assertEqual('barbarbaz', encoderactor.foo().result())

    def test_suspendthis(self):
        encoderactor = self.x.spawn(Encoder(None))
        self.assertEqual(100, encoderactor.hmm().result())

    def test_sharedmailbox(self):
        sums = [Sum() for _ in range(5)]
        a = self.x.spawn(*sums)
        invokeall([a.plus(1).result for _ in range(100)])
        self.assertEqual(100, sum(s.s for s in sums))
        print([s.s for s in sums])
        raise
