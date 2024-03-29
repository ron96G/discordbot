import logging
from asyncio import AbstractEventLoop, Future, Task, get_running_loop, sleep
from typing import Dict, Optional

from common import Context, format_exception
from discord.ext.commands import Bot
from discord.voice_client import VoiceClient

from .track import Track
from .track_queue import TrackQueue


class QueueRunner:
    log = logging.getLogger("runner")
    bot: Bot
    loop: AbstractEventLoop
    track_queue: TrackQueue
    background_tasks: Dict[str, Task] = dict()

    def __init__(
        self,
        bot: Bot,
        track_queue: TrackQueue,
        loop: Optional[AbstractEventLoop] = None,
    ):
        self.bot = bot
        self.loop = loop or get_running_loop()
        self.track_queue = track_queue

    def __del__(self):
        for key in self.track_queue.keys():
            self.remove(key)

    def find_relevant_voice_client(self, guild_id: str) -> VoiceClient:
        self.log.debug(f"Trying to match voice_client for guild {guild_id}")
        for c in self.bot.voice_clients:
            if c.guild.id == guild_id:
                return c
        self.log.debug(f"Guild {guild_id} does not have a voice_client")
        return None

    def _task_callback(self, future: Future):
        e = future.exception()
        if e is not None:
            self.log.error(e)

    def register(self, id: str):
        if not self.track_queue.has(id):
            self.track_queue.new(id)

        task = self.loop.create_task(self.run(guild_id=id))
        self.background_tasks[id] = task
        task.add_done_callback(self._task_callback)

    def remove(self, id: str):
        if self.track_queue.has(id):
            self.log.info(f"Removing queue for {id}")
            self.track_queue.remove(id)

        if id in self.background_tasks:
            task = self.background_tasks[id]
            if not task.done():
                task.cancel()
            else:
                if task.exception() is not None:
                    self.log.warn(
                        f"Task for {id} raised an exception: {task.exception()}"
                    )
            del self.background_tasks[id]

    async def play(
        self,
        guild_id: str,
        voice_client: VoiceClient,
        track: Track,
        cur_try=0,
        max_try=3,
    ):
        if voice_client is not None:
            ctx = track.context

            def handle_error(e: Exception, ctx: Context):
                msg = format_exception(e)
                self.log.warn(f"{guild_id}: Error in queue_runner: {msg}")
                ctx.reply_formatted_error(f"Failed to play: {msg}")

            async with ctx.typing():
                cur_try += 1

                try:
                    player = await track.next()
                    if track.is_failed():
                        await ctx.reply_formatted_error(
                            f"Failed to play due to {track.error}"
                        )
                        return

                    voice_client.play(
                        player,
                        after=lambda e: handle_error(e, ctx) if e else None,
                    )

                    title = "Bottich Audio Player"
                    if track.hasNext():
                        await self.track_queue.put_back(guild_id, track)
                        title = (
                            f"Bottich Audio Player ({track.current}/{track.max_len()})"
                        )

                    info = track.get_current_info()
                    self.log.info(f"Playing track: {info.pretty_print()}")

                    await ctx.reply_formatted_msg(
                        f'Now playing "{info.title}"',
                        title=title,
                        thumbnail_url=info.thumbnail,
                    )

                except Exception as e:
                    self.log.warn(
                        f"{guild_id}: Failed to play audio in queue {guild_id}: {e}"
                    )
                    info = track.get_current_info()

                    if cur_try >= max_try:
                        self.log.warn(f"Failed to play {info.title}. Retrying...", e)
                        return await self.play(
                            guild_id, voice_client, track, cur_try, max_try
                        )
                    else:
                        self.log.error(
                            "Failed to play {info.title}. Exceeded retry limit", e
                        )
                        await ctx.reply_formatted_error(
                            f"Failed to play {info.title}. Skipping..."
                        )
                finally:
                    self.log.debug(f"{guild_id}: Popping item from queue")
                    self.track_queue.task_done(guild_id)

    async def run(self, guild_id: str):
        self.log.info(f"{guild_id}: Started queue_runner")

        voice_client = self.find_relevant_voice_client(guild_id)

        while not self.bot.is_closed():
            voice_client = self.find_relevant_voice_client(guild_id)
            if (
                voice_client is not None
                and voice_client.is_connected()
                and not voice_client.is_playing()
                and not voice_client.is_paused()
            ):

                self.log.info(f"{guild_id}: Getting new track from queue")
                track: Track = (
                    await self.track_queue.get(guild_id)
                ).item  # this blocks until a track is available
                self.log.info(f"Got new track from queue: {track.pretty_print()}")

                if not voice_client.is_connected():
                    voice_client = self.find_relevant_voice_client(guild_id)

                if voice_client is not None:
                    await self.play(guild_id, voice_client, track, 0, 3)

            await sleep(1)
