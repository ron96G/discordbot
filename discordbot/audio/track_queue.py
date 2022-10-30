import logging
from asyncio import AbstractEventLoop, QueueFull, get_running_loop
from typing import Dict, List, Optional

from .priority_queue import AwarePriorityQueue
from .track import Track


class TrackQueue:
    log = logging.getLogger("track_queue")
    queue: Dict[str, AwarePriorityQueue]
    maxsize: int
    loop: AbstractEventLoop

    def __init__(self, maxsize=20, loop: Optional[AbstractEventLoop] = None):
        self.maxsize = maxsize
        self.queue = {}
        self.loop = loop or get_running_loop()

    def __len__(self):
        return len(self.queue)

    def _get_queue(self, id: str) -> AwarePriorityQueue:
        if self.has(id):
            return self.queue[id]

    def content(self, id: str) -> List[Track]:
        """Returns the current content of the queue with id."""
        if self.has(id):
            return self.queue[id].content()

    def empty(self, id: str):
        if self.has(id):
            return self.queue[id].empty()

    def size(self, id: str) -> int:
        if self.has(id):
            return self.queue[id].qsize()

    def has(self, id: str):
        return self.queue.get(id) is not None

    def keys(self):
        return self.queue.keys()

    def new(self, id: str):
        """Create a new queue for id."""
        if self.has(id):
            raise ValueError(f"{id} already exists")
        else:
            self.queue[id] = AwarePriorityQueue(maxsize=self.maxsize, loop=self.loop)
        return self.queue[id]

    def remove(self, id: str):
        """Remove the queue with id."""
        if self.has(id):
            self.log.info(f"Removing queue {id}")
            del self.queue[id]

    def clear(self, id: str):
        """Clear the queue with id by removing the queue entirely."""
        if self.has(id):
            self.log.info(f"Clearing queue {id}")
            self.queue[id] = AwarePriorityQueue(maxsize=self.maxsize, loop=self.loop)

    def pop(self, id: str):
        """Pop the first item from the queue."""
        queue = self.queue.get(id)
        if queue is not None:
            try:
                queue.get_nowait()
            except:
                pass
            else:
                queue.task_done()

    def task_done(self, id: str):
        if self.has(id):
            self.queue[id].task_done()

    async def put(self, id: str, tracks: List[Track], prio=999, create_new=False):
        if not isinstance(tracks, list):
            tracks = [tracks]
        queue = self.queue.get(id)
        if queue is None and create_new:
            if not create_new:
                raise ValueError(f"Queue for {id} does not exist")
            queue = self.new(id)

        try:
            for track in tracks:
                track.priority = prio
                queue.put_nowait(track.as_prio_item())

        except QueueFull as e:
            raise ValueError("Queue is full. Skipping...")
        except Exception as e:
            raise ValueError(e)

    async def put_back(self, id: str, tracks: List[Track]):
        await self.put(id, tracks, 900)

    async def get(self, id: str) -> Track:
        self.log.info(f"{id}: Getting new track")
        queue = self.queue.get(id)
        if queue is None:
            raise ValueError(f"{id}: Queue does not exist")
        else:
            return await queue.get()
