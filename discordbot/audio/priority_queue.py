import logging
from asyncio import AbstractEventLoop, PriorityQueue
from typing import List


class Item:
    priority: int


class AwarePriorityQueue:
    """(workaround) Minimized implementation of PriorityQueue that makes the entire content accessible."""

    log = logging.getLogger("priority_queue")
    _queue: PriorityQueue
    _current_prio: int
    _content: List[Item]

    def __init__(self, maxsize: int, loop: AbstractEventLoop):
        self._queue = PriorityQueue(maxsize, loop=loop)
        self._content = []
        self._current_prio = None

    def __del__(self):
        del self._queue
        del self._content

    def content(self):
        return self._content

    def empty(self):
        return self._queue.empty()

    def full(self):
        return self._queue.full()

    def qsize(self):
        return self._queue.qsize()

    def task_done(self):
        return self._queue.task_done()

    async def get(self):
        item = await self._queue.get()
        self._pop()
        return item

    def get_nowait(self):
        try:
            item = self._queue.get_nowait()
        except Exception as e:
            raise e

        self._pop()
        return item

    def _higher_prio(self, prio: int):
        return self._current_prio <= prio

    def _pop(self) -> Item:
        """Pop the first item in the content list.
        Should only be used after the item was already removed from the internal queue.
        """
        self._content.pop()
        if len(self._content) > 0:
            self._current_prio = self._content[0].priority
        else:
            self._current_prio = None

        self.log.debug(f"Current prio is {self._current_prio}")
        self.log.debug(f"Content is {self._content}")

    def _put(self, item: Item):
        if self._current_prio is None:
            self._current_prio = item.priority

        if self._higher_prio(item.priority):
            self._current_prio = item.priority
            self._content.insert(0, item)
        else:
            self._content.append(item)

    def put_nowait(self, item: Item):
        try:
            self._queue.put_nowait(item)
        except Exception as e:
            raise e

        if self._current_prio is None:
            self._current_prio = item.priority

        self._put(item)
