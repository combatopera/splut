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

from .bg import SimpleBackground
from collections import namedtuple
import threading, logging, time, bisect, math

log = logging.getLogger(__name__)

# The taskindex ensures task objects are never compared:
class Task(namedtuple('BaseTask', 'when taskindex task')):

    def __call__(self):
        try:
            self.task()
        except Exception:
            log.exception('Task failed:')

class Delay(SimpleBackground):

    def __init__(self):
        self.taskindex = 0
        self.tasks = []

    def start(self):
        self.sleeper = self.Sleeper()
        self.taskslock = threading.RLock()
        super().start(self._bg, self.sleeper)

    def _insert(self, when, task):
        t = Task(when, self.taskindex, task)
        self.taskindex += 1
        self.tasks.insert(bisect.bisect(self.tasks, t), t)

    def after(self, delay, task):
        self.at(time.time() + delay, task)

    def at(self, when, task):
        with self.taskslock:
            self._insert(when, task)
        self.sleeper.interrupt()

    def popall(self):
        with self.taskslock:
            tasks = self.tasks.copy()
            self.tasks.clear()
            return tasks

    def _pop(self, now):
        i = bisect.bisect(self.tasks, (now, math.inf))
        tasks = self.tasks[:i]
        del self.tasks[:i]
        return tasks

    def _bg(self, sleeper):
        while not self.quit:
            with self.taskslock:
                tasks = self._pop(time.time())
            for task in tasks:
                task()
            with self.taskslock:
                sleeptime = self.tasks[0].when - time.time() if self.tasks else None
            sleeper.sleep(sleeptime)
        with self.taskslock:
            log.debug("Tasks denied: %s", len(self.tasks))
