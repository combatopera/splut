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

import threading, logging, tempfile, shutil, os, time

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

    def start(self, bg, *interruptibles):
        self.quit = Quit([i.interrupt for i in interruptibles])
        self.thread = threading.Thread(name = type(self).__name__, target = bg, args = interruptibles)
        self.thread.start()

    def stop(self):
        self.quit.fire()
        self.thread.join()

class Profile:

    def __init__(self, time, sort = 'time', path = 'profile'):
        self.time = time
        self.sort = sort
        self.path = path

class MainBackground(SimpleBackground):

    def __init__(self, config):
        if config.profile:
            if config.trace:
                raise Exception
            self.profilesort = config.profile.sort
            self.profilepath = config.profile.path
            self.bg = self.profile
        elif config.trace:
            self.bg = self.trace
        else:
            self.bg = self

    def start(self, *interruptibles):
        super().start(self.bg, *interruptibles)

    def profile(self, *args, **kwargs):
        profilepath = self.profilepath + time.strftime('.%Y-%m-%dT%H-%M-%S')
        tmpdir = tempfile.mkdtemp()
        try:
            binpath = os.path.join(tmpdir, 'stats')
            import cProfile
            cProfile.runctx('self.__call__(*args, **kwargs)', globals(), locals(), binpath)
            import pstats
            with open(profilepath, 'w') as f:
                stats = pstats.Stats(binpath, stream = f)
                stats.sort_stats(self.profilesort)
                stats.print_stats()
                f.flush() # XXX: Why?
        finally:
            shutil.rmtree(tmpdir)

    def trace(self, *args, **kwargs):
        from trace import Trace
        t = Trace()
        t.runctx('self.__call__(*args, **kwargs)', globals(), locals())
        t.results().write_results()