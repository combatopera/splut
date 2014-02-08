#!/usr/bin/env python

from __future__ import division
import numpy as np, random
from pym2149.buf import MasterBuf, Buf
from pym2149.minblep import MinBleps
from pym2149.nod import AbstractNode, Block

class Wave16:

  bytespersample = 2

  def __init__(self, path, rate):
    self.f = open(path, 'wb') # Binary.
    self.f.write('RIFF')
    self.skip(4)
    self.f.write('WAVEfmt ') # Observe trailing space.
    self.writen(16) # Chunk data size.
    self.writen(1, 2) # PCM (uncompressed).
    channels = 1
    self.writen(channels, 2)
    self.writen(rate)
    bytesperframe = self.bytespersample * channels
    self.writen(rate * bytesperframe) # Bytes per second.
    self.writen(bytesperframe, 2)
    self.writen(self.bytespersample * 8, 2) # Bits per sample.
    self.f.write('data')
    self.skip(4)
    self.dirty = True
    self.cleanifnecessary()

  def skip(self, n):
    self.f.seek(n, 1)

  def writen(self, n, size = 4): # Not for public use.
    for _ in xrange(size):
      self.f.write(chr(n & 0xff))
      n >>= 8

  def block(self, buf):
    buf.tofile(self.f)
    self.dirty = True

  def cleanifnecessary(self):
    if self.dirty:
      fsize = self.f.tell()
      self.f.seek(4)
      self.writen(fsize - 8) # Size of RIFF.
      self.f.seek(40)
      self.writen(fsize - 44) # Size of data.
      self.f.seek(fsize)
      self.dirty = False

  def flush(self):
    self.cleanifnecessary()
    self.f.flush()

  def close(self):
    self.cleanifnecessary()
    self.f.close() # Implicit flush.

class WavWriter(AbstractNode):

  outrate = 44100

  def __init__(self, clock, chip, path):
    AbstractNode.__init__(self)
    scale = 500 # Smaller values result in worse-looking spectrograms.
    dtype = np.float32 # Effectively about 24 bits.
    self.diffmaster = MasterBuf(dtype = dtype)
    self.outmaster = MasterBuf(dtype = dtype)
    self.wavmaster = MasterBuf(dtype = np.int16)
    self.mixinmaster = MasterBuf(dtype = dtype)
    self.minbleps = MinBleps(scale)
    self.overflowsize = self.minbleps.maxmixinsize() - 1 # Sufficient for any mixin at last sample.
    self.carrybuf = Buf(np.empty(self.overflowsize, dtype = dtype))
    self.f = Wave16(path, self.outrate)
    self.naivex = 0
    self.dc = 0 # Last naive value of previous block.
    self.outz = 0 # Absolute index of first output sample being processed in this iteration.
    self.carrybuf.fill(self.dc) # Initial carry can be the initial dc level.
    self.naiverate = clock
    self.chip = chip

  def callimpl(self):
    blockbuf = self.chain(self.chip)
    framecount = len(blockbuf)
    diffbuf = self.diffmaster.differentiate(self.dc, blockbuf)
    out0 = self.outz
    # Index of the first sample we can't output yet:
    self.outz = self.minbleps.getoutindexandshape(self.naivex + framecount, self.naiverate, self.outrate)[0]
    # Make space for all samples we can output plus overflow:
    outbuf = self.outmaster.ensureandcrop(self.outz - out0 + self.overflowsize)
    # Paste in the carry followed by the carried dc level:
    outbuf.buf[:self.overflowsize] = self.carrybuf.buf
    outbuf.buf[self.overflowsize:] = self.dc
    for naivey in diffbuf.nonzeros():
      amp = diffbuf.buf[naivey]
      outi, mixin, mixinsize = self.minbleps.getmixin(self.naivex + naivey, self.naiverate, self.outrate, amp, self.mixinmaster)
      outj = outi + mixinsize
      outbuf.buf[outi - out0:outj - out0] += mixin.buf
      outbuf.buf[outj - out0:] += amp
    wavbuf = self.wavmaster.ensureandcrop(self.outz - out0)
    wavbuf.buf[:] = outbuf.buf[:self.outz - out0]
    self.f.block(wavbuf)
    self.carrybuf.buf[:] = outbuf.buf[self.outz - out0:]
    self.naivex += framecount
    self.dc = blockbuf.buf[-1]

  def flush(self):
    self.f.flush()

  def close(self):
    self.f.close()

class Chip(AbstractNode):

  naiverate = 2000000

  def __init__(self):
    AbstractNode.__init__(self)
    tonefreq = 1500
    toneamp = .25 * 2 ** 15
    self.naivesize = self.naiverate * 60 # One minute of data.
    toneoscscale = 16 # A property of the chip.
    periodreg = int(round(self.naiverate / (toneoscscale * tonefreq)))
    period = toneoscscale * periodreg # Even.
    self.naivebuf = Buf(np.empty(self.naivesize))
    x = 0
    while x < self.naivesize:
      self.naivebuf.fillpart(x, x + period // 2, toneamp)
      self.naivebuf.fillpart(x + period // 2, x + period, -toneamp)
      x += period
    self.cursor = 0

  def callimpl(self):
    self.cursor += self.block.framecount
    return Buf(self.naivebuf.buf[self.cursor - self.block.framecount:self.cursor])

def main():
  chip = Chip()
  stream = WavWriter(chip.naiverate, chip, 'minbleppoc.wav')
  while chip.cursor < chip.naivesize:
    stream.call(Block(random.randint(1, 30000)))
  stream.close()

if __name__ == '__main__':
  main()
