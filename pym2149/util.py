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

import time, logging
from diapyr import types
from .iface import Started

log = logging.getLogger(__name__)

def singleton(f):
    return f()

def awaitinterrupt(config):
    if config.profile or config.trace:
        sleeptime = config.profile.time if config.profile else config.trace
        log.debug("Continue for %.3f seconds.", sleeptime)
        time.sleep(sleeptime)
        log.debug('End of profile, shutting down.')
    else:
        log.debug('Continue until interrupt.')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log.debug('Caught interrupt, shutting down.')

class EMA:

    def __init__(self, alpha, initial):
        self.alpha = alpha
        self.value = initial

    def __call__(self, instantaneous):
        self.value = self.alpha * instantaneous + (1 - self.alpha) * self.value
        return self.value

def ceildiv(numerator, denominator):
    return (numerator + denominator - 1) // denominator

def starter(startabletype):
    class StartedImpl(Started):
        @types(startabletype)
        def __init__(self, startable):
            startable.start()
            self.startable = startable
        def __del__(self):
            log.debug("Stopping: %s.%s", startabletype.__module__, startabletype.__name__)
            self.startable.stop()
    return StartedImpl
