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
        try:
            method = getattr(obj, self.methodname)
        except AttributeError:
            pass
        else:
            return partial(self._fire, obj, method)

    def _fire(self, obj, method, mailbox):
        if iscoroutinefunction(method):
            Coro(obj, method(*self.args, **self.kwargs)).fire(nulloutcome, self.future, mailbox)
        else:
            try:
                obj = method(*self.args, **self.kwargs)
            except BaseException as e:
                self.future.set(AbruptOutcome(e))
            else:
                self.future.set(NormalOutcome(obj))

class AMessage:

    def __init__(self, coro, outcome, future):
        self.coro = coro
        self.outcome = outcome
        self.future = future

    def resolve(self, obj):
        if obj is self.coro.obj:
            return partial(self.coro.fire, self.outcome, self.future)

class Coro:

    def __init__(self, obj, coro):
        self.obj = obj
        self.coro = coro

    def fire(self, outcome, future, mailbox):
        try:
            s = outcome.propagate(self.coro)
        except StopIteration as e:
            future.set(NormalOutcome(e.value))
        except BaseException as e:
            future.set(AbruptOutcome(e))
        else:
            def post(f):
                mailbox.add(AMessage(self, f.get(), future))
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
        cls = type(f"{''.join({type(obj).__name__: None for obj in objs})}Actor", (), {f.__name__: f for f in [__getattr__]})
        actor = cls()
        for obj in objs:
            obj.actor = actor
        return actor
