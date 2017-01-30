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

from __future__ import division
import struct

def parse(v):
    return (Bundle if v.startswith('#bundle\0') else Message)(v)

class Reader:

    seconds1970 = 25567 * 24 * 60 * 60
    fractionlimit = 1 << 32

    def __init__(self, v):
        self.c = 0
        self.v = v

    def consume(self, n):
        self.c += n
        return self.v[self.c - n:self.c]

    def timetag(self):
        seconds1900, fraction = struct.unpack('>II', self.consume(8))
        return seconds1900 - self.seconds1970 + fraction / self.fractionlimit

    def int32(self):
        return struct.unpack('>i', self.consume(4))[0]

    def __nonzero__(self):
        return self.c < len(self.v)

    def element(self):
        return parse(self.consume(self.int32()))

    def string(self):
        text = self.consume(self.v.index('\0', self.c) - self.c).decode('ascii')
        self.c += 1 # Consume at least one null.
        self.align()
        return text

    def align(self):
        self.c += (-self.c) % 4

    def float32(self):
        return struct.unpack('>f', self.consume(4))[0]

    def blob(self):
        blob = self.consume(self.int32())
        self.align()
        return blob

class Bundle:

    def __init__(self, v):
        r = Reader(v)
        r.string()
        self.timetag = r.timetag()
        self.elements = []
        while r:
            self.elements.append(r.element())

class Message:

    types = {
        'i': Reader.int32,
        's': Reader.string,
        'f': Reader.float32,
        'b': Reader.blob,
    }

    def __init__(self, v):
        r = Reader(v)
        self.addrpattern = r.string()
        self.args = []
        for tt in r.string()[1:]:
            self.args.append(self.types[tt](r))