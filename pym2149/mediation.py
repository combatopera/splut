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

import logging
from const import midichannelcount

log = logging.getLogger(__name__)

class Mediation:

    interruptingformat = "[%s] Interrupting note on channel."

    def __init__(self, midichanbase, chipchancount, warn = log.warn):
        self.midichanandnotetochipchan = {}
        self.chipchantomidichanandnote = [(None, None)] * chipchancount
        self.midichantochipchanhistory = dict([midichanbase + i, range(chipchancount)] for i in xrange(midichannelcount))
        self.chipchantoonframe = [None] * chipchancount
        self.warn = warn

    def acquirechipchan(self, midichan, midinote, frame):
        if (midichan, midinote) in self.midichanandnotetochipchan:
            return self.midichanandnotetochipchan[midichan, midinote] # Spurious case.
        chipchanhistory = self.midichantochipchanhistory[midichan]
        def acquire(chipchan):
            self.midichanandnotetochipchan[midichan, midinote] = chipchan
            self.chipchantomidichanandnote[chipchan] = [midichan, midinote]
            del chipchanhistory[i]
            chipchanhistory.insert(0, chipchan)
            self.chipchantoonframe[chipchan] = frame
            return chipchan
        offchipchans = set()
        for chipchan, midichanandnote in enumerate(self.chipchantomidichanandnote):
            if midichanandnote[1] is None:
                offchipchans.add(chipchan)
        if offchipchans:
            for i, chipchan in enumerate(chipchanhistory):
                if chipchan in offchipchans:
                    return acquire(chipchan)
        else:
            bestonframe = min(self.chipchantoonframe) # May be None.
            bestchipchans = set(c for c, f in enumerate(self.chipchantoonframe) if f == bestonframe)
            for i, chipchan in enumerate(chipchanhistory):
                if chipchan in bestchipchans:
                    self.warn(self.interruptingformat, chr(ord('A') + chipchan))
                    self.releasechipchan(*self.chipchantomidichanandnote[chipchan])
                    return acquire(chipchan)

    def releasechipchan(self, midichan, midinote):
        chipchan = self.midichanandnotetochipchan.pop((midichan, midinote), None)
        if chipchan is not None: # Non-spurious case.
            self.chipchantomidichanandnote[chipchan][1] = None
            return chipchan

    def currentmidichanandnote(self, chipchan):
        return self.chipchantomidichanandnote[chipchan]
