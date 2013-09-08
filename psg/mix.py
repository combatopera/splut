from buf import *

class Mixer:

  def __init__(self, *streams):
    self.buf = SimpleBuf()
    self.streams = streams

  def __call__(self, buf, samplecount):
    self.streams[0](buf, samplecount)
    self.buf.atleast(samplecount)
    for stream in self.streams[1:]:
      stream(self.buf, samplecount)
      buf.add(self.buf[:samplecount])
