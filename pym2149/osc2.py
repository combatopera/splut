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

from nod import BufNode
from ring import signaldtype
from pyrbo import turbo, LOCAL
from const import u1, u4, i4
import numpy as np

class Shape:

    pyrbotype = dict(buf = [signaldtype], size = u4, introlen = u4)

    def __init__(self, g, introlen = 0):
        self.buf = np.fromiter(g, signaldtype)
        self.size = self.buf.size
        self.introlen = introlen

class ShapeOsc(BufNode):

    progresstype = u4

    def __init__(self, scale, periodreg):
        BufNode.__init__(self, signaldtype)
        self.stepsize = 0
        self.scale = scale
        self.periodreg = periodreg

    def reset(self, shape):
        self.index = -1
        self.progress = np.iinfo(self.progresstype).max
        self.shape = shape

    def callimpl(self):
        self.index, self.progress, self.stepsize = self.shapeimpl()

    @turbo(
        self = dict(
            blockbuf = dict(buf = [signaldtype]),
            block = dict(framecount = u4),
            index = i4,
            progress = progresstype,
            stepsize = u4,
            scale = u4,
            periodreg = dict(value = u4),
            shape = Shape.pyrbotype,
            eager = u1,
        ),
        i = u4,
        j = u4,
        n = u4,
        val = signaldtype,
    )
    def shapeimpl(self):
        self_blockbuf_buf = self_block_framecount = self_index = self_progress = self_scale = self_periodreg_value = self_shape_buf = self_shape_size = self_shape_introlen = self_eager = LOCAL
        if self_eager:
            self_stepsize = self_periodreg_value * self_scale
        i = 0
        if self_progress < self_stepsize:
            val = self_shape_buf[self_index]
            j = min(self_stepsize - self_progress, self_block_framecount)
            while i < j:
                self_blockbuf_buf[i] = val
                i += 1
        if i == self_block_framecount:
            self_progress += self_block_framecount
        else:
            if not self_eager:
                self_stepsize = self_periodreg_value * self_scale
            n = (self_block_framecount - i) // self_stepsize
            while n:
                self_index += 1
                if self_index == self_shape_size:
                    self_index = self_shape_introlen
                val = self_shape_buf[self_index]
                j = i + self_stepsize
                while i < j:
                    self_blockbuf_buf[i] = val
                    i += 1
                n -= 1
            if i == self_block_framecount:
                self_progress = self_stepsize
            else:
                self_index += 1
                if self_index == self_shape_size:
                    self_index = self_shape_introlen
                val = self_shape_buf[self_index]
                self_progress = self_block_framecount - i
                while i < self_block_framecount:
                    self_blockbuf_buf[i] = val
                    i += 1
        return self_index, self_progress, self_stepsize

class ToneOsc(ShapeOsc):

    eager = True
    shape = Shape([1, 0])

    def __init__(self, scale, periodreg):
        scaleofstep = scale * 2 // 2 # Normally half of 16.
        ShapeOsc.__init__(self, scaleofstep, periodreg)
        self.reset(self.shape)

class NoiseOsc(ShapeOsc):

    eager = False

    def __init__(self, scale, periodreg, shape):
        scaleofstep = scale * 2 # This results in authentic spectrum, see qnoispec.
        ShapeOsc.__init__(self, scaleofstep, periodreg)
        self.reset(shape)
