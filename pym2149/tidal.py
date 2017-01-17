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
from const import clientname
from diapyr import types
from iface import Config, Stream, Chip
from pll import PLL
from bg import SimpleBackground, MainBackground
from channels import Channels
from minblep import MinBleps
from timer import Timer
from util import EMA
from speed import SpeedDetector
from midi import MidiSchedule
import native.calsa as calsa, logging, time

log = logging.getLogger(__name__)

class TidalListen(SimpleBackground):

    @types(Config, PLL)
    def __init__(self, config, pll):
        self.chanbase = config.midichannelbase
        self.programbase = config.midiprogrambase
        self.pllignoremidichans = set(config.performancechannels)
        log.info("MIDI channels not significant for PLL: {%s}", ', '.join(str(c) for c in sorted(self.pllignoremidichans)))
        self.pll = pll

    def start(self):
        SimpleBackground.start(self, self.bg, calsa.Client(clientname, "%s IN" % clientname))

    def bg(self, client):
        while not self.quit:
            event = client.event_input()
            if event is not None:
                eventobj = self.classes[event.type](self, event)
                self.pll.event(event.time, eventobj, eventobj.midichan not in self.pllignoremidichans)

class TidalPump(MainBackground):

    @types(Config, TidalListen, Channels, MinBleps, Stream, Chip, Timer, PLL)
    def __init__(self, config, midi, channels, minbleps, stream, chip, timer, pll):
        MainBackground.__init__(self, config)
        self.updaterate = config.updaterate
        self.performancemidichans = set(config.performancechannels)
        self.skipenabled = config.midiskipenabled
        self.speeddetector = SpeedDetector(10) if config.speeddetector else lambda eventcount: None
        self.midi = midi
        self.channels = channels
        self.minbleps = minbleps
        self.stream = stream
        self.chip = chip
        self.timer = timer
        self.pll = pll

    def __call__(self):
        schedule = MidiSchedule(self.updaterate, self.skipenabled)
        while not self.quit:
            update = self.pll.takeupdateimpl(schedule.awaittaketime())
            schedule.step(update.idealtaketime)
            scheduledevents = 0
            for event in update.events:
                if event.midichan not in self.performancemidichans:
                    scheduledevents += 1
            self.speeddetector(scheduledevents)
            timecode = self.channels.frameindex
            if self.speeddetector.speedphase is not None:
                speed = self.speeddetector.speedphase[0]
                timecode = "%s*%s+%s" % (timecode // speed, speed, timecode % speed)
            chanandnotetoevents = {}
            for event in update.events:
                if isinstance(event, NoteOnOff):
                    try:
                        chanandnotetoevents[event.midichan, event.midinote].append(event)
                    except KeyError:
                        chanandnotetoevents[event.midichan, event.midinote] = [event]
            # Apply all channel state events first:
            sortedevents = [event for event in update.events if isinstance(event, ChannelStateMessage)]
            # Then all notes that end up off:
            for noteevents in chanandnotetoevents.itervalues():
                if NoteOff == noteevents[-1].__class__:
                    sortedevents.extend(noteevents)
            # Then all notes that end up on:
            for noteevents in chanandnotetoevents.itervalues():
                if NoteOn == noteevents[-1].__class__:
                    sortedevents.extend(noteevents)
            for event in sortedevents:
                log.debug("%.6f %s @ %s -> %s", event.offset, event, timecode, event(self.channels))
            self.channels.updateall()
            for block in self.timer.blocksforperiod(self.updaterate):
                self.stream.call(block)
            self.channels.closeframe()
        self.stream.flush()
