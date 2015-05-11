# Copyright 2014 Andrzej Cichocki

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

from reg import Reg

prescalers = 0, 4, 10, 16, 50, 64, 100, 200
mfpclock = 2457600

class MFPTimer:

    def __init__(self):
        self.control = Reg()
        self.data = Reg()
        self.rtoneperiod = Reg()
        # Signal period is double the interrupt period, so mul by 2:
        self.rtoneperiod.link(lambda tcr, tdr: prescalers[tcr] * tdr * 2, self.control, self.data)
        self.control.value = 0
        self.data.value = 0
        self.rtoneflag = Reg()
        self.rtoneflag.value = False

    def update(self, tcr, tdr):
        self.control.value = tcr
        self.data.value = tdr
        self.rtoneflag.value = True
