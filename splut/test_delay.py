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

from .delay import Delay
from unittest import TestCase

class TestDelay(TestCase):

    def test_simultaneous(self):
        d = Delay()
        def f(): pass
        def g(): pass
        d._insert(500, f)
        d._insert(500, g)
        self.assertEqual([], d._pop(499.9))
        self.assertEqual([f, g], [t.task for t in d._pop(500)])
