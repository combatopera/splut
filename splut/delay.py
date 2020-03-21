# Copyright 2014, 2018, 2019, 2020 Andrzej Cichocki

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

from .bg import SimpleBackground, Sleeper
from collections import namedtuple
import heapq, logging, threading, time

log = logging.getLogger(__name__)

# The taskindex ensures task objects are never compared:
class Task(namedtuple('BaseTask', 'when taskindex task')):

    def __call__(self):
        try:
            self.task()
        except Exception:
            log.exception('Task failed:')

class Delay(SimpleBackground):

    taskindex = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = []

    def start(self):
        self.sleeper = Sleeper()
        self.taskslock = threading.RLock()
        super().start(self._bg, self.sleeper)

    def popall(self):
        with self.taskslock:
            tasks = self.tasks.copy()
            self.tasks.clear()
            return tasks

    def _bg(self, sleeper):
        while not self.quit:
            sleeper.sleep(self.sleeptime())
        with self.taskslock:
            log.debug("Tasks denied: %s", len(self.tasks))

    def _insert(self, when, task):
        heapq.heappush(self.tasks, Task(when, self.taskindex, task))
        self.taskindex += 1

    def at(self, when, task):
        with self.taskslock:
            self._insert(when, task)
        self.sleeper.interrupt()

    def after(self, delay, task):
        self.at(time.time() + delay, task)

    def _pop(self, now):
        def g():
            while self.tasks and self.tasks[0].when <= now:
                yield heapq.heappop(self.tasks)
        return list(g())

    def sleeptime(self):
        with self.taskslock:
            tasks = self._pop(time.time())
        for task in tasks:
            task()
        with self.taskslock:
            if self.tasks:
                return self.tasks[0].when - time.time()
