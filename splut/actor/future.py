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

from threading import Condition

class NormalOutcome:

    def __init__(self, obj):
        self.obj = obj

    def propagate(self, coro):
        return coro.send(self.obj)

    def result(self):
        return self.obj

class AbruptOutcome:

    def __init__(self, e):
        self.e = e

    def propagate(self, coro):
        return coro.throw(self.e)

    def result(self):
        raise self.e

class Future:

    def __init__(self):
        self.condition = Condition()
        self.callbacks = []
        self.outcome = None

    def set(self, outcome):
        assert outcome is not None
        with self.condition:
            assert self.outcome is None
            self.outcome = outcome
            self.condition.notify_all()
            callbacks, self.callbacks = self.callbacks, None
        for f in callbacks:
            f(outcome)

    def get(self):
        with self.condition:
            while True:
                outcome = self.outcome
                if outcome is not None:
                    return outcome
                self.condition.wait()

    def wait(self):
        return self.get().result()

    def listenoutcome(self, f):
        with self.condition:
            if self.callbacks is not None:
                self.callbacks.append(f)
                return
            outcome = self.outcome
        f(outcome)

    def __await__(self):
        return (yield self)
