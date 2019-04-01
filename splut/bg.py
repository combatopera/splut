# Copyright 2014, 2018, 2019 Andrzej Cichocki

# This file is part of splut.
#
# splut is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# splut is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with splut.  If not, see <http://www.gnu.org/licenses/>.

from functools import partial
import threading, logging, tempfile, os, time

log = logging.getLogger(__name__)

class Quit:

    def __init__(self, interrupts):
        self.quit = False
        self.interrupts = interrupts

    def fire(self):
        self.quit = True
        for interrupt in self.interrupts:
            interrupt()

    def __bool__(self):
        return self.quit

class SimpleBackground:

    daemon = False

    class Sleeper:

        def __init__(self):
            self.cv = threading.Condition()
            self.interrupted = False

        def sleep(self, t):
            with self.cv:
                if self.interrupted or self.cv.wait(t):
                    self.interrupted = False

        def interrupt(self):
            with self.cv:
                self.interrupted = True
                self.cv.notify() # There should be at most one.

    def __init__(self, profile = None):
        self.profile = profile

    def start(self, bg, *interruptibles):
        self.quit = Quit([i.interrupt for i in interruptibles])
        target = bg if self.profile is None else partial(self.profile, bg)
        self.thread = threading.Thread(name = type(self).__name__, target = target, args = interruptibles, daemon = self.daemon)
        self.thread.start()

    def stop(self):
        self.quit.fire()
        self.thread.join()

class Profile:

    def __init__(self, time, sort = 'time'):
        self.time = time
        self.sort = sort

    def __call__(self, target, *args, **kwargs):
        profilepath = threading.current_thread().name + time.strftime('.%Y-%m-%dT%H-%M-%S')
        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, 'stats')
            import cProfile
            cProfile.runctx('target(*args, **kwargs)', globals(), locals(), binpath)
            import pstats
            with open(profilepath, 'w') as f:
                stats = pstats.Stats(binpath, stream = f)
                stats.sort_stats(self.sort)
                stats.print_stats()

class MainBackground(SimpleBackground):

    def __init__(self, config):
        super().__init__(config.profile)
        if config.trace:
            if config.profile:
                raise Exception # XXX: Can they really not be combined?
            self.bg = self.trace
        else:
            self.bg = self

    def start(self, *interruptibles):
        super().start(self.bg, *interruptibles)

    def trace(self, *args, **kwargs):
        from trace import Trace
        t = Trace()
        t.runctx('self.__call__(*args, **kwargs)', globals(), locals())
        t.results().write_results()
