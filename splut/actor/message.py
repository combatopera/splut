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

from .future import AbruptOutcome, NormalOutcome
from diapyr.util import innerclass
from functools import partial
from inspect import iscoroutinefunction

nulloutcome = NormalOutcome(None)

class Message:

    def __init__(self, methodname, args, kwargs, future):
        self.methodname = methodname
        self.args = args
        self.kwargs = kwargs
        self.future = future

    def taskornone(self, obj, mailbox):
        try:
            method = getattr(obj, self.methodname)
        except AttributeError:
            return
        if iscoroutinefunction(method):
            return partial(Coro(obj, method(*self.args, **self.kwargs), self.future).fire, nulloutcome, mailbox)
        return partial(self._fire, method, mailbox)

    def _fire(self, method, mailbox):
        try:
            value = method(*self.args, **self.kwargs)
        except BaseException as e:
            self.future.set(AbruptOutcome(e))
        else:
            self.future.set(NormalOutcome(value))

class Coro:

    @innerclass
    class Message:

        def __init__(self, outcome):
            self.outcome = outcome

        def taskornone(self, obj, mailbox):
            if obj is self.obj:
                return partial(self.fire, self.outcome, mailbox)

    def __init__(self, obj, coro, future):
        self.obj = obj
        self.coro = coro
        self.future = future

    def fire(self, outcome, mailbox):
        try:
            g = outcome.propagate(self.coro)
        except StopIteration as e:
            self.future.set(NormalOutcome(e.value))
        except BaseException as e:
            self.future.set(AbruptOutcome(e))
        else:
            try:
                listenoutcome = g.listenoutcome
            except AttributeError:
                self.future.set(AbruptOutcome(RuntimeError(f"Unusable yield: {g}")))
            else:
                listenoutcome(lambda o: mailbox.add(self.Message(o)))
