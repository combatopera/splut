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

from concurrent.futures import Future
from functools import partial
from queue import Empty, Queue
from threading import Semaphore

class Inbox:

    def __init__(self, executor, obj):
        self.queue = Queue()
        self.cork = Semaphore()
        self.executor = executor
        self.obj = obj

    def add(self, message):
        self.queue.put(message)
        if self.cork.acquire(False):
            self.executor.submit(self._drain)

    def _drain(self):
        try:
            while True:
                self.queue.get_nowait().fire(self)
        except Empty:
            self.cork.release()

class Message:

    def __init__(self, method, future = None):
        self.method = method
        self.future = Future() if future is None else future

    def fire(self, inbox):
        try:
            r = self.method()
        except Suspension as s:
            s.catch(inbox, self.future)
        except BaseException as e:
            self.future.set_exception(e)
        else:
            self.future.set_result(r)

class Exchange:

    def __init__(self, executor):
        self.executor = executor

    def spawn(self, obj):
        class Actor:
            def __getattr__(self, name):
                def actormethod(*args, **kwargs):
                    message = Message(partial(method, *args, **kwargs))
                    inbox.add(message)
                    return message.future
                method = getattr(obj, name)
                return actormethod
        inbox = Inbox(self.executor, obj)
        return Actor()

class Suspension(BaseException):

    @property
    def future(self):
        return self.args[0]

    @property
    def then(self):
        return self.args[1]

    def catch(self, inbox, messagefuture):
        def callback(f):
            inbox.add(Message(partial(self.then, f), messagefuture))
        self.future.add_done_callback(callback)

def suspend(future):
    def decorator(then):
        raise Suspension(future, then)
    return decorator
