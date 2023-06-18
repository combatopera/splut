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

from .future import Future
from .mailbox import Mailbox
from .message import Message
from functools import partial

class Spawn:

    def __init__(self, executor):
        self.executor = executor

    def __call__(self, *objs):
        def post(name, *args, **kwargs):
            future = Future()
            mailbox.add(Message(name, args, kwargs, future))
            return future
        def __getattr__(self, name):
            return partial(post, name)
        mailbox = Mailbox(self.executor, objs)
        return type(f"{''.join({type(obj).__name__: None for obj in objs})}Actor", (), {f.__name__: f for f in [__getattr__]})()
