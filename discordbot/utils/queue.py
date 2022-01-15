import asyncio
import logging
from asyncio.queues import Queue
from asyncio.tasks import Task
from datetime import datetime, timedelta

from discord.errors import DiscordException
from discord.ext import commands
from discord.voice_client import VoiceClient
from music_utils.ytdl import YTDLSource

# in seconds
VOICE_CLIENT_INACTIVITY_TIMEOUT = 60


class Item:
    def __init__(self, task: Task, q: Queue):
        self.task = task
        self.q = q

    def __del__(self):
        print("Canceling task")
        self.task.cancel()


class BotQueue:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger("queue")
        self.loop = bot.loop or asyncio.get_event_loop()
        self._queueDict = dict()
        self.lock = asyncio.Lock()

    async def register(self, identifier: str, maxsize=20):
        async with self.lock:
            if not self.exists(identifier):
                q = asyncio.Queue(maxsize=maxsize, loop=self.loop)

                task = self.loop.create_task(
                    self.queue_runner(queue=q, guild_id=identifier)
                )
                self.log.info(f"Created queue_runner for {identifier}")
                self._queueDict[identifier] = Item(task, q)
                self.default_maxsize = maxsize

    async def deregister(self, identifier: str):
        async with self.lock:
            if self.exists(identifier):
                self.log.info(f"Removing queue for {identifier}")
                del self._queueDict[identifier]

    def exists(self, identifier: str):
        return identifier in self._queueDict

    async def clear(self, identifier: str):
        if self.exists(identifier):
            q = self._queueDict[identifier].q
            size = q.qsize()
            for _ in range(size):
                q.get_nowait()
                q.task_done()

            return size
        return 0

    def pop(self, identifier: str):
        if self.exists(identifier):
            q = self._queueDict[identifier].q
            q.get_nowait()
            q.task_done()

    def size(self, identifier: str):
        if self.exists(identifier):
            return self._queueDict[identifier].q.qsize()
        return 0

    async def put(self, identifier: str, item):
        self._queueDict[identifier].q.put_nowait(item)
        self.log.info(f"Added new item to queue {identifier}")
        return self._queueDict[identifier].q.qsize()

    def find_relevant_voice_client(self, guild_id: str) -> VoiceClient:
        self.log.debug(f"Trying to match voice_client for guild {guild_id}")
        for c in self.bot.voice_clients:
            if c.guild.id == guild_id:
                return c
        self.log.debug(f"Guild {guild_id} does not have a voice_client")
        return None

    async def queue_runner(self, queue: asyncio.Queue, guild_id: str):
        await self.bot.wait_until_ready()
        log = self.log

        log.info(f"{guild_id}: Started queue_runner")

        not_connceted_deadline: datetime = None
        voice_client = self.find_relevant_voice_client(guild_id)

        def handle_error(self, e: Exception, ctx: commands.Context):
            log.error(f"{guild_id}: Error in queue_runner: {e}")
            ctx.send(f"**Failed to play**: {repr(e)}")

        while not self.bot.is_closed():
            if voice_client is None or not voice_client.is_connected():
                # there might be a new voice_client that is used...
                voice_client = self.find_relevant_voice_client(guild_id)

                if voice_client is None:
                    if not_connceted_deadline is None:
                        log.info(
                            f"{guild_id}: Flagged queue_runner {guild_id} for inactivity"
                        )
                        not_connceted_deadline = datetime.now() + timedelta(
                            0, VOICE_CLIENT_INACTIVITY_TIMEOUT
                        )

                    elif not_connceted_deadline < datetime.now():
                        return await self.deregister(guild_id)

            elif not voice_client.is_playing():
                log.info(f"{guild_id}: Getting new item from queue")
                item = await queue.get()
                if item is not None:
                    ctx: commands.Context = item["ctx"]
                    async with ctx.typing():
                        try:
                            log.debug(f"{guild_id}: Waiting for player to be ready")
                            player: YTDLSource = await item["player"]
                            if player is None:
                                raise DiscordException(
                                    "Player could not be constructed"
                                )

                            if player.error is not None:
                                log.warn(
                                    f"{guild_id}: Player exception: {player.error}"
                                )
                                await ctx.message.reply(
                                    f"**Failed to play**: {repr(player.error)}"
                                )

                            else:
                                track = player.title
                                author = ctx.author.name
                                log.info(
                                    f'{guild_id}: Selected next track "{author}: {track}"'
                                )
                                voice_client.play(
                                    player,
                                    after=lambda e: handle_error(e, ctx) if e else None,
                                )
                                await ctx.send(
                                    f'Now playing "{track}" requested by "{author}"'
                                )

                        except Exception as e:
                            log.warn(
                                f"{guild_id}: Failed to play audio in queue {guild_id}: {e}"
                            )
                            await ctx.send(
                                f"Failed to play {track} requested by {author}. Skipping..."
                            )

                        finally:
                            log.debug(f"{guild_id}: Popping item from queue")
                            queue.task_done()
                else:
                    log.debug(f"{guild_id}: Skipping empty item")

            await asyncio.sleep(1)
