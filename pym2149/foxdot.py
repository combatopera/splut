# Copyright 2014, 2018, 2019 Andrzej Cichocki

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

from . import osctrl
from .bg import SimpleBackground
from .iface import Config
from .midi import NoteOn
from .pll import PLL
from diapyr import types
import logging, socket, re

log = logging.getLogger(__name__)

class Handler:

    @types()
    def __init__(self): pass

class SCSynthHandler(Handler): pass

class SCLangHandler(Handler): pass

class NullCommand(SCSynthHandler):

    addresses = '/g_freeAll', '/dumpOSC'

    def __call__(self, *args): pass

class GetInfo(SCLangHandler):

    addresses = '/foxdot/info',
    audiochans = 100
    inputchans = 2
    outputchans = 2
    buffers = 1024

    def __call__(self, timetags, message, reply, addevent):
        reply(osctrl.Message('/foxdot/info', [0, 0, 0, 0,
                self.audiochans, 0,
                self.inputchans,
                self.outputchans,
                self.buffers, 0, 0]).ser())

class LoadSynthDef(SCLangHandler):

    addresses = '/foxdot',

    def __call__(self, timetags, message, reply, addevent):
        path, = message.args
        log.debug("Ignore SynthDef: %s", path)

class NewGroup(SCSynthHandler):

    addresses = '/g_new',

    def __call__(self, timetags, message, reply, addevent):
        id, action, target = message.args

class FoxDotEvent:

    def __init__(self, timetag, channel, note, velocity):
        self.timetag = timetag
        self.channel = channel
        self.note = note
        self.velocity = velocity

class NewSynth(SCSynthHandler):

    addresses = '/s_new',

    @types(Config)
    def __init__(self, config):
        self.playerregex = re.compile(config.playerregex)
        self.firstchanord = ord(config.firstchannelchar)
        self.chipchannels = config.chipchannels
        self.neutralvel = config.neutralvelocity

    def __call__(self, timetags, message, reply, addevent):
        name, id, action, target = message.args[:4]
        controls = dict(zip(*(message.args[x::2] for x in [4, 5])))
        try:
            player, midinote, amp = (controls[k] for k in ['player', 'midinote', 'amp'])
        except KeyError:
            return
        m = self.playerregex.fullmatch(player)
        if m is not None:
            timetag, = timetags
            addevent(FoxDotEvent(
                    timetag,
                    (ord(m.group(1)) - self.firstchanord) % self.chipchannels,
                    midinote,
                    round(amp * self.neutralvel)))

class FoxDotClient:

    def __init__(self, chancount, host, port, bufsize, handlers, label):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # XXX: Close it?
        self.sock.settimeout(.1) # For polling the open flag.
        self.sock.bind((host, port))
        self.chancount = chancount
        self.bufsize = bufsize
        self.handlers = handlers
        self.label = label

    def eventsortimeout(self):
        events = []
        try:
            bytes, address = self.sock.recvfrom(self.bufsize)
            self._message(address, [], osctrl.parse(bytes), events.append)
        except socket.timeout:
            pass
        return events

    def _message(self, udpaddr, timetags, message, addevent):
        try:
            addrpattern = message.addrpattern
        except AttributeError:
            self._elements(udpaddr, timetags + [message.timetag], message.elements, addevent)
            return
        try:
            handler = self.handlers[addrpattern]
        except KeyError:
            log.warn("Unhandled %s message: %s", self.label, message)
            return
        handler(timetags, message, lambda reply: self.sock.sendto(reply, udpaddr), addevent)

    def _elements(self, udpaddr, timetags, elements, addevent):
        for element in elements:
            self._message(udpaddr, timetags, element, addevent)

    def interrupt(self):
        self.open = False

class FoxDotListen(SimpleBackground):

    def __init__(self, config, pll, handlers):
        self.config = config
        self.pll = pll
        self.handlers = {a: h for h in handlers for a in h.addresses}

    def start(self):
        config = self.config['FoxDot', self.configkey]
        super().start(self.bg, FoxDotClient(
                self.config.chipchannels,
                *(config.resolved(name).unravel() for name in ['host', 'port', 'bufsize']),
                self.handlers,
                self.configkey))

    def bg(self, client):
        while not self.quit:
            for event in client.eventsortimeout():
                self.pll.event(event.timetag, NoteOn(self.config, event), True)

class SCSynth(FoxDotListen):

    configkey = 'scsynth'

    @types(Config, PLL, [SCSynthHandler])
    def __init__(self, config, pll, handlers):
        super().__init__(config, pll, handlers)

class SCLang(FoxDotListen):

    configkey = 'sclang'

    @types(Config, PLL, [SCLangHandler])
    def __init__(self, config, pll, handlers):
        super().__init__(config, pll, handlers)

def configure(di):
    di.add(NullCommand)
    di.add(GetInfo)
    di.add(LoadSynthDef)
    di.add(NewGroup)
    di.add(NewSynth)
    di.add(SCSynth)
    di.add(SCLang)
