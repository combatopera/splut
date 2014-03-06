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

from pym2149.util import Timer
from pym2149.buf import singleton
from pym2149.ym2149 import stclock as clock
from pym2149.out import WavWriter
from pym2149.mix import IdealMixer
from cli import Config

@singleton
class voidnote:

  def noteon(self, chip, chan):
    chip.levelmodes[chan].value = 0
    chip.toneflags[chan].value = False
    chip.noiseflags[chan].value = False

  def update(self, chip, chan, frameindex):
    pass

class NoteAction:

  def __init__(self, note):
    self.note = note

  def onnoteornone(self, chip, chan):
    self.note.noteon(chip, chan)
    return self.note

@singleton
class sustainaction:

  def onnoteornone(self, chip, chan):
    pass

def getorlast(v, i):
  try:
    return v[i]
  except IndexError:
    return v[-1]

class Orc(dict):

  def __init__(self, ticksperbar):
    self.timers = []
    self.ticksperbar = ticksperbar

  def add(self, cls):
    try:
      key = cls.char
    except AttributeError:
      key = cls.__name__[0]
    if key in self:
      raise KeyError(key) # XXX: An abuse?
    self[key] = cls
    return cls

  def __enter__(self):
    self.timers.append(Timer(self.ticksperbar, None))
    return OrcTimer(self, self.timers[-1])

  def __exit__(self, exc_type, exc_value, traceback):
    self.timers.pop() # It will log non-zero carry.

class OrcTimer:

  voidaction = NoteAction(voidnote)

  def __init__(self, orc, timer):
    self.orc = orc
    self.timer = timer

  def __call__(self, beatsperbar, beats, *args, **kwargs):
    frames = []
    paramindex = 0
    for char in beats:
      if '.' == char:
        action = sustainaction
      elif '-' == char:
        action = self.voidaction
      else:
        nargs = [getorlast(v, paramindex) for v in args]
        nkwargs = dict([k, getorlast(v, paramindex)] for k, v in kwargs.iteritems())
        action = NoteAction(self.orc[char](*nargs, **nkwargs))
        paramindex += 1
      frames.append(action)
      b, = self.timer.blocks(beatsperbar)
      for _ in xrange(b.framecount - 1):
        frames.append(sustainaction)
    return frames

class Updater:

  def __init__(self, onnote, chip, chan, frameindex):
    self.onnote = onnote
    self.chip = chip
    self.chan = chan
    self.frameindex = frameindex

  def update(self, frameindex):
    self.onnote.update(self.chip, self.chan, frameindex - self.frameindex)

@singleton
class voidupdater:

  def update(self, frameindex):
    pass

class Main:

  def __init__(self, refreshrate):
    self.refreshrate = refreshrate

  def __call__(self, frames):
    config = Config()
    outpath, = config.args
    chip = config.createchip(clock)
    stream = WavWriter(chip.clock, IdealMixer(chip), outpath)
    try:
      timer = Timer(chip.clock)
      chanupdaters = [voidupdater] * chip.channels
      for frameindex, frame in enumerate(frames):
        for patternindex, action in enumerate(frame):
          chan = patternindex # TODO LATER: Utilise voids in channels.
          onnoteornone = action.onnoteornone(chip, chan)
          if onnoteornone is not None:
            chanupdaters[chan] = Updater(onnoteornone, chip, chan, frameindex)
        for updater in chanupdaters:
          updater.update(frameindex)
        for b in timer.blocks(self.refreshrate):
          stream.call(b)
      stream.flush()
    finally:
      stream.close()
