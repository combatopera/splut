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

from .future import AbruptOutcome, Future, NormalOutcome
from functools import partial
from threading import Lock

class Mailbox:

    ttl = None

    def __init__(self, executor):
        self.queue = []
        self.lock = Lock()
        self.executor = executor

    def add(self, message):
        with self.lock:
            self.queue.append(message)
            if self.ttl is None:
                self.ttl = 1
                self.executor.submit(self._drain)
            else:
                self.ttl += 1

    def _drain(self):
        while True:
            with self.lock:
                if not self.ttl:
                    del self.ttl
                    break
                self.ttl -= 1
                message = self.queue.pop(0)
            message.fire(self)

class Message:

    def __init__(self, method, future):
        self.method = method
        self.future = future

    def fire(self, mailbox):
        try:
            obj = self.method()
        except Suspension as s:
            s.catch(mailbox, self.future)
        except BaseException as e:
            self.future.set(AbruptOutcome(e))
        else:
            self.future.set(NormalOutcome(obj))

class Exchange:

    def __init__(self, executor):
        self.executor = executor

    def spawn(self, obj):
        def __getattr__(self, name):
            def post(*args, **kwargs):
                future = Future()
                mailbox.add(Message(partial(method, *args, **kwargs), future))
                return future
            method = getattr(obj, name)
            return post
        mailbox = Mailbox(self.executor)
        cls = type(f"{type(obj).__name__}Actor", (), {f.__name__: f for f in [__getattr__]})
        obj.actor = actor = cls()
        return actor

class Suspension(BaseException):

    @property
    def futures(self):
        return self.args[0]

    @property
    def then(self):
        return self.args[1]

    def catch(self, mailbox, messagefuture):
        def post(f):
            mailbox.add(Message(partial(self.then, f), messagefuture))
        for f in self.futures:
            f.add_done_callback(post)

def suspend(*futures):
    def decorator(then):
        raise Suspension(futures, then)
    return decorator
