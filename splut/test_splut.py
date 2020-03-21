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

from . import invokeall
from functools import partial
from unittest import TestCase

def good(value):
    return value

def bad(e):
    raise e

class TestInvokeAll(TestCase):

    def test_generator(self):
        with self.assertRaises(TypeError):
            invokeall(_ for _ in [])

    def test_happypath(self):
        self.assertEqual([], invokeall([]))
        self.assertEqual([50], invokeall([partial(good, 50)]))
        self.assertEqual([100, 200], invokeall((partial(good, 100), partial(good, 200))))

    def test_1fail(self):
        e1 = Exception(1)
        with self.assertRaises(Exception) as cm:
            invokeall([partial(good, 123), partial(bad, e1)])
        self.assertIs(e1, cm.exception)

    def test_2fails(self):
        e1 = Exception(1)
        e2 = Exception(2)
        with self.assertRaises(Exception) as cm:
            invokeall([partial(bad, e1), partial(good, 456), partial(bad, e2)])
        self.assertIs(e2, cm.exception)
        self.assertIs(e1, cm.exception.__context__)

    def test_3fails(self):
        e1 = Exception(1)
        e2 = Exception(2)
        e3 = Exception(3)
        with self.assertRaises(Exception) as cm:
            invokeall([partial(bad, e1), partial(bad, e2), partial(bad, e3)])
        # When cm.exception is printed these will appear in the order they were raised:
        self.assertIs(e3, cm.exception)
        self.assertIs(e2, cm.exception.__context__)
        self.assertIs(e1, cm.exception.__context__.__context__)
