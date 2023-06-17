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
from .mailbox import Mailbox
from functools import partial
from inspect import iscoroutinefunction

nulloutcome = NormalOutcome(None)

class Message:

    def __init__(self, methodname, args, kwargs, future):
        self.methodname = methodname
        self.args = args
        self.kwargs = kwargs
        self.future = future

    def resolve(self, obj):
        return partial(self._fire, getattr(obj, self.methodname))

    def _fire(self, method, mailbox):
        if iscoroutinefunction(method):
            _corofire(method(*self.args, **self.kwargs), nulloutcome, self.future, mailbox)
        else:
            try:
                obj = method(*self.args, **self.kwargs)
            except BaseException as e:
                self.future.set(AbruptOutcome(e))
            else:
                self.future.set(NormalOutcome(obj))

class AMessage:

    def __init__(self, c, outcome, future):
        self.c = c
        self.outcome = outcome
        self.future = future

    def resolve(self, obj):
        return self._fire

    def _fire(self, mailbox):
        _corofire(self.c, self.outcome, self.future, mailbox)

def _corofire(coro, outcome, future, mailbox):
    try:
        s = outcome.propagate(coro)
    except StopIteration as e:
        future.set(NormalOutcome(e.value))
    except BaseException as e:
        future.set(AbruptOutcome(e))
    else:
        def post(f):
            mailbox.add(AMessage(coro, f.get(), future))
        for f in s.futures:
            f.addcallback(post)

class Exchange:

    def __init__(self, executor):
        self.executor = executor

    def spawn(self, *objs):
        def __getattr__(self, name):
            def post(*args, **kwargs):
                future = Future()
                mailbox.add(Message(name, args, kwargs, future))
                return future
            return post
        mailbox = Mailbox(self.executor, objs)
        t, = {type(obj) for obj in objs}
        cls = type(f"{t.__name__}Actor", (), {f.__name__: f for f in [__getattr__]})
        actor = cls()
        for obj in objs:
            obj.actor = actor
        return actor
