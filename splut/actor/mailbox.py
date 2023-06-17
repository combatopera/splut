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

from threading import Lock

class Worker:

    def __init__(self, obj):
        self.idle = True
        self.obj = obj

class Mailbox:

    def __init__(self, executor, objs):
        self.queue = []
        self.lock = Lock()
        self.executor = executor
        self.workers = [Worker(obj) for obj in objs]

    def add(self, message):
        with self.lock:
            for worker in self.workers:
                if worker.idle:
                    fire = message.resolve(worker.obj)
                    if fire is not None:
                        self.executor.submit(self._run, worker, fire)
                        worker.idle = False
                        break
            else:
                self.queue.append(message)

    def _another(self, worker):
        with self.lock:
            for i, message in enumerate(self.queue):
                fire = message.resolve(worker.obj)
                if fire is not None:
                    self.queue.pop(i)
                    return fire
            worker.idle = True

    def _run(self, worker, fire):
        while True:
            fire(self)
            fire = self._another(worker)
            if fire is None:
                break
