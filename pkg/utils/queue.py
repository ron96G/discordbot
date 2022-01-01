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


    def register(self, identifier: str, maxsize=20):
        q = asyncio.Queue(maxsize=maxsize, loop=self.loop)
        
        task = self.loop.create_task(self.queue_runner(queue=q, guild_id=identifier))
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


    def find_relevant_voice_client(self, guild_id: str) -> VoiceClient:
        self.log.info(f'Trying to match voice_client for guild {guild_id}')
        for c in self.bot.voice_clients:
            if c.guild.id == guild_id:
                return c
        self.log.info(f'Guild {guild_id} does not have a voice_client')
        return None

    async def queue_runner(self, queue: asyncio.Queue, guild_id: str):
        await self.bot.wait_until_ready()
        self.log.info('Started queue_runner')

        not_connceted_deadline: datetime = None
        voice_client = self.find_relevant_voice_client(guild_id)

        while not self.bot.is_closed():

            if not voice_client.is_connected():
                # there might be a new voice_client that is used...
                voice_client = self.find_relevant_voice_client(guild_id)

                if voice_client is None:
                    if not_connceted_deadline is None:
                        self.log.info(f'Flagged queue_runner {guild_id} for inactivity')
                        not_connceted_deadline = datetime.now() + timedelta(0, VOICE_CLIENT_INACTIVITY_TIMEOUT)

                    elif not_connceted_deadline < datetime.now():
                        return self.deregister(guild_id)

            elif not voice_client.is_playing():
                self.log.info('Getting new item from queue')
                item = await queue.get()
                if item is not None:
                    with item['ctx'].typing():
                        author = item['ctx'].author.name
                        track = item['player'].title
                        voice_client.play(await item['player'])
                        self.log.info(f'Playing track of {author}: {track}')
                        await item['ctx'].send(f'Now playing {track} requested by {author}')
                        queue.task_done()

            await asyncio.sleep(1)