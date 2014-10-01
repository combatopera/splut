#!/usr/bin/env python

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
from pym2149.initlogging import logging
from pym2149.jackclient import JackClient
from pym2149.nod import Block
from config import getprocessconfig
import pypm, sys

log = logging.getLogger(__name__)

class Midi:

  def __enter__(self):
    pypm.Initialize()
    return self

  def selectdevice(self):
    for i in xrange(pypm.CountDevices()):
      info = pypm.GetDeviceInfo(i)
      if info[2]: # It's an input device.
        print >> sys.stderr, "%2d) %s" % (i, info[1])
    print >> sys.stderr, 'Index? ',
    return Device(int(raw_input())) # Apparently int ignores whitespace.

  def __exit__(self, *args):
    pypm.Terminate()

class Device:

  def __init__(self, index):
    self.index = index

  def start(self):
    self.input = pypm.Input(self.index) # Deferring this helps avoid PortMidi buffer overflow.

  def iterevents(self):
    while self.input.Poll():
      event, = self.input.Read(1)
      event, _ = event # XXX: What is the second field?
      yield event

def main():
  config = getprocessconfig()
  with Midi() as midi:
    device = midi.selectdevice()
    with JackClient(config) as jackclient:
      chip, stream = jackclient.newchipandstream(None)
      try:
        log.debug("JACK block size: %s or %.3f seconds", stream.size, stream.size / config.getoutputrate())
        minbleps = stream.wavs[0].minbleps
        naivex = 0
        device.start()
        while True:
          for event in device.iterevents():
            print event
          # Make min amount of chip data to get one JACK block:
          naiven = minbleps.getminnaiven(naivex, stream.size)
          stream.call(Block(naiven))
          naivex = (naivex + naiven) % chip.clock
      finally:
        stream.close()

if '__main__' == __name__:
  main()
