import asyncio, logging
from datetime import datetime, timedelta
from asyncio.queues import Queue
from asyncio.tasks import Task

from discord.ext import commands
from discord.voice_client import VoiceClient

# in seconds
VOICE_CLIENT_INACTIVITY_TIMEOUT = 60

class Item():
    def __init__(self, task: Task, q: Queue):
        self.task = task
        self.q = q

    def __del__(self):
        print('Canceling task')
        self.task.cancel()

class BotQueue():
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger('queue')
        self.loop = bot.loop or asyncio.get_event_loop()
        self._queueDict = dict()


    def register(self, identifier: str, voiceClient : VoiceClient, maxsize=20):
        q = asyncio.Queue(maxsize=maxsize, loop=self.loop)
        
        task = self.loop.create_task(self.queue_runner(queue=q, voiceClient=voiceClient, identifier=identifier))
        self.log.info(f'Created queue_runner for {identifier}')
        self._queueDict[identifier] = Item(task, q)
        self.default_maxsize = maxsize

    def deregister(self, identifier: str):
        if self.exists(identifier):
            self.log.info(f'Removing queue for {identifier}')
            del self._queueDict[identifier]

    def exists(self, identifier: str):
        return identifier in self._queueDict

    async def clear(self, identifier: str):
        if self.exists(identifier):
            q = self._queueDict[identifier].q
            size = q.qsize()
            for _  in range(size):
                q.get_nowait()
                q.task_done()

            return size
        return 0

    def size(self, identifier: str):
        if self.exists(identifier):
            return self._queueDict[identifier].q.qsize()
        return 0

    async def put(self, identifier: str, item):
        self._queueDict[identifier].q.put_nowait(item)
        return self._queueDict[identifier].q.qsize()

    async def queue_runner(self, queue: asyncio.Queue, voiceClient : VoiceClient, identifier: str):
        await self.bot.wait_until_ready()
        self.log.info('Started queue_runner')

        not_connceted_deadline: datetime = None

        while not self.bot.is_closed():

            if not voiceClient.is_connected():
                if not_connceted_deadline is None:
                    self.log.info(f'Flagged queue_runner {identifier} for inactivity')
                    not_connceted_deadline = datetime.now() + timedelta(0, VOICE_CLIENT_INACTIVITY_TIMEOUT)
                elif not_connceted_deadline < datetime.now():
                    return self.deregister(identifier)

            if voiceClient.is_connected() and not voiceClient.is_playing():
                self.log.info('Getting new item from queue')
                item = await queue.get()
                if item is not None:
                    author = item['ctx'].author.name
                    track = item['player'].title
                    self.log.info(f'Playing track of {author}: {track}')
                    voiceClient.play(item['player'])
                    queue.task_done()
                    await item['ctx'].send(f'Now playing {track} requested by {author}')

            await asyncio.sleep(1)