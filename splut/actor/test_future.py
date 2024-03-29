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

from .future import AbruptOutcome, Future, NormalOutcome
from unittest import TestCase

class TestFuture(TestCase):

    def test_works(self):
        def c(o):
            v.append(o.result())
        def d(o):
            v.append(o.result() + 1)
        v = []
        f = Future()
        f.listenoutcome(c)
        with self.assertRaises(AssertionError):
            f.set(None)
        f.set(NormalOutcome(100))
        self.assertEqual([100], v)
        f.listenoutcome(d)
        self.assertEqual([100, 101], v)
        with self.assertRaises(AssertionError):
            f.set(NormalOutcome(200))
        self.assertEqual([100, 101], v)

    def test_abrupt(self):
        class X(Exception):
            pass
        f = Future()
        x = X()
        f.set(AbruptOutcome(x))
        with self.assertRaises(X) as cm:
            f.wait()
        self.assertIs(cm.exception, x)
