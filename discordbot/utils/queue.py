import asyncio
import logging
from asyncio.queues import Queue
from asyncio.tasks import Task
from typing import Dict, Union

import discord
import music_utils
from cogs.func import Context
from cogs.text_to_speech import SynthesizeSpeechSource
from discord.errors import DiscordException
from discord.ext import commands
from discord.voice_client import VoiceClient

# in seconds
VOICE_CLIENT_INACTIVITY_TIMEOUT = 60


class Item:
    _task: asyncio.Task
    _q: asyncio.Queue

    def __init__(self, task: Task, q: Queue):
        self._task: asyncio.Task = task
        self._q: asyncio.Queue = q

    def __del__(self):
        if not self._task.done():
            self._task.cancel()


class BotQueue:
    _queueDict: Dict[str, Item]

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
                task = self._queueDict[identifier]._task
                if not task.done():
                    task.cancel()
                else:
                    if task.exception() is not None:
                        self.log.warn(
                            f"Task for {identifier} raised an exception: {task.exception()}"
                        )

                del self._queueDict[identifier]

    def exists(self, identifier: str):
        exists = identifier in self._queueDict
        return exists

    async def clear(self, identifier: str):
        if self.exists(identifier):
            q = self._queueDict[identifier]._q
            size = q.qsize()
            for _ in range(size):
                q.get_nowait()
                q.task_done()

            return size
        return 0

    def pop(self, identifier: str):
        if self.exists(identifier):
            q = self._queueDict[identifier]._q
            q.get_nowait()
            q.task_done()

    def size(self, identifier: str):
        if self.exists(identifier):
            return self._queueDict[identifier]._q.qsize()
        return 0

    async def put(self, identifier: str, item):
        if self.exists(identifier):
            self._queueDict[identifier]._q.put_nowait(item)
            self.log.info(f"Added new item to queue {identifier}")
            return self._queueDict[identifier]._q.qsize()
        else:
            self.log.warn(f"Tried to put item into nonexistent queue")

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

        voice_client = self.find_relevant_voice_client(guild_id)

        def handle_error(e: Exception, ctx: Context):
            msg = music_utils.format_exception(e)
            log.warn(f"{guild_id}: Error in queue_runner: {msg}")
            ctx.reply_formatted_error(f"Failed to play: {msg}")

        while not self.bot.is_closed():
            if not voice_client.is_playing():

                if voice_client is None or not voice_client.is_connected():
                    # there might be a new voice_client that is used...
                    voice_client = self.find_relevant_voice_client(guild_id)

                log.info(f"{guild_id}: Getting new item from queue")
                item = await queue.get()  # this blocks until an item is available

                if item is not None and voice_client is not None:

                    ctx: Context = item["ctx"]
                    async with ctx.typing():
                        try:
                            log.debug(f"{guild_id}: Waiting for player to be ready")
                            player: Union[
                                music_utils.YTDLSource, SynthesizeSpeechSource
                            ] = await item["player"]
                            if player is None:
                                raise DiscordException(
                                    "Player could not be constructed"
                                )

                            if player.error is not None:
                                msg = music_utils.format_exception(player.error)
                                log.warn(f"{guild_id}: Player exception: {msg}")
                                await ctx.reply_formatted_error(
                                    f"Failed to play: {msg}"
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

                                await ctx.reply_formatted_msg(
                                    f'Now playing "{track}"',
                                    title="Bottich Audio Player",
                                    thumbnail_url=item["thumbnail"],
                                )

                        except Exception as e:
                            log.warn(
                                f"{guild_id}: Failed to play audio in queue {guild_id}: {e}"
                            )
                            await ctx.reply_formatted_error(
                                f"Failed to play {track}. Skipping..."
                            )

                        finally:
                            log.debug(f"{guild_id}: Popping item from queue")
                            queue.task_done()

            await asyncio.sleep(1)
