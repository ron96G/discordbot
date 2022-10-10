import asyncio
import datetime
import logging
import mimetypes
import os
import traceback
from typing import List

import boto3
import discord
import spotipy
from audio import LinksService, SpotifyService, YoutubeService
from cogs import Config, Func, Music, TextToSpeech, Wikipedia
from common.config import ConfigMap
from common.config_store import ConfigStore
from common.context import Context
from discord.errors import HTTPException, NotFound
from discord.ext import commands
from discord.message import Attachment, Message
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyClientCredentials

LEAVE_AFTER_INACTIVITY_DELAY = 120
LEAVE_AFTER_INACTIVITY_DURATION = 600


class Bot(commands.Bot):
    configstore: ConfigStore

    def __init__(
        self,
        command_prefix,
        description,
        configstore: ConfigStore,
        configmap: ConfigMap = None,
        dir="./uploads/",
    ):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=command_prefix, description=description, intents=intents
        )
        self.log = logging.getLogger("bot")
        self.dir = dir
        self.config = configmap or ConfigMap(self, [])
        self.configstore = configstore

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    async def setup_hook(self):
        await self.add_cog(Config(self))
        await self.add_cog(Func(self))

        t2s = TextToSpeech(
            self,
            boto3.client(
                "polly",
                aws_access_key_id=self.configstore.get("ACCESS_KEY"),
                aws_secret_access_key=self.configstore.get("SECRET_KEY"),
                region_name="eu-central-1",
            ),
        )
        await self.add_cog(t2s)
        await self.add_cog(Wikipedia(self, t2s))

        spotify = None
        SPOTIFY_CLIENT_ID = self.configstore.get("SPOTIFY_CLIENT_ID")
        SPOTIFY_CLIENT_SECRET = self.configstore.get("SPOTIFY_CLIENT_SECRET")

        if SPOTIFY_CLIENT_ID is not None and SPOTIFY_CLIENT_SECRET is not None:
            s = spotipy.Spotify(
                client_credentials_manager=SpotifyClientCredentials(
                    client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
                )
            )
            spotify = SpotifyService(s)

        youtube = None
        YOUTUBE_API_KEY = self.configstore.get("YOUTUBE_API_KEY")
        if YOUTUBE_API_KEY is not None:
            service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            youtube = YoutubeService(service)

        links = LinksService()

        music = Music(self, youtube, spotify, links)
        await self.add_cog(music)
        self.track_queue = music.queue
        self.queue_runner = music.runner

        debug_enabled = self.configstore.get_env_first("DEBUG") in ["true", "True"]
        debug_enabled = True
        if debug_enabled:
            self.log.warn("Currently no debugging cog available")

    async def on_ready(self):
        self.log.info(f"Logged in as {self.user.name} with id {self.user.id}")

        for guild in self.guilds:
            id = guild.id
            if not self.config.exists(id):
                self.config.set_defaults_for(id)

        self.loop.create_task(self.leave_after_inactivity())

    async def get_context(self, message, *, cls=Context):
        return await super().get_context(message, cls=cls)

    async def on_command_error(self, ctx: Context, error: commands.CommandError):
        self.log.warn(
            f'{ctx.guild.id}: "{ctx.author.display_name}" using "{ctx.command}" failed with: {error}'
        )

        if isinstance(error, commands.CommandInvokeError):
            await ctx.reply_formatted_error(error.original)
        else:
            await ctx.reply_formatted_error(error)

    async def on_error(self, event_method, *args, **kwargs):
        self.log.error(f"Unknown error: {traceback.print_exc()}")

    async def on_message_delete(self, message: Message):
        self.log.info(f"message by {message.author} was deleted: {message.content}")

    async def on_message(self, message: Message):
        if message.author.id == self.user.id:
            return

        self.log.info(
            f'Received message from {message.author.display_name}: "{message.content}" with {len(message.attachments)} attachments'
        )

        await self.process_commands(message)
        await self.handle_attachments(message.attachments)

    async def handle_attachments(self, attachments: List[Attachment]) -> None:
        if attachments is None:
            return
        for a in attachments:
            output = os.path.join(
                self.dir, f"{a.id}{mimetypes.guess_extension(a.content_type)}"
            )
            try:
                await a.save(output)
            except (HTTPException, NotFound) as e:
                raise commands.CommandError("unable to handle attachment", e)

    async def join_author(self, ctx: commands.Context):
        if ctx.author.voice:
            if ctx.voice_client is not None:
                return await ctx.voice_client.move_to(ctx.author.voice.channel)
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You are not connected to a voice channel")

    async def leave_after_inactivity(self):
        marked_for_inactivity = {}

        while not self.is_closed():
            now = datetime.datetime.now()

            for voice_client in self.voice_clients:
                voice_client: discord.VoiceClient = voice_client

                if not voice_client.is_playing() and not voice_client.is_paused():
                    id = voice_client.guild.id
                    if id not in marked_for_inactivity:
                        self.log.info(f"Flagged voice_client of {id} for inactivity")
                        marked_for_inactivity[id] = {
                            "timestamp": now,
                            "voice_client": voice_client,
                        }

            left = []
            for id in marked_for_inactivity.keys():
                if (
                    marked_for_inactivity[id]["timestamp"]
                    + datetime.timedelta(0, LEAVE_AFTER_INACTIVITY_DURATION)
                    < now
                ):
                    # remove it due to inactivity
                    self.log.info(
                        f"Disconnecting voice_client of {id} due to inactivity"
                    )
                    voice_client: discord.VoiceClient = marked_for_inactivity[id][
                        "voice_client"
                    ]
                    await asyncio.gather(
                        voice_client.disconnect(), self.track_queue.remove(id)
                    )
                    left.append(id)

            for id in left:
                del marked_for_inactivity[id]

            await asyncio.sleep(LEAVE_AFTER_INACTIVITY_DELAY)
