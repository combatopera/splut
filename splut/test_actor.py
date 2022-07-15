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
from unittest import TestCase

class Sum:

    s = 0

    def plus(self, x):
        self.s += x
        return self.s

class TestExchange(TestCase):

    def test_works(self):
        with ThreadPoolExecutor() as e:
            exchange = Exchange(e)
            sumactor = exchange.spawn(Sum())
            f = sumactor.plus(5)
            g = sumactor.plus(2)
            self.assertEqual(5, f.result())
            self.assertEqual(7, g.result())
