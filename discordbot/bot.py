import asyncio
import datetime
import logging
import mimetypes
import os
import traceback
from typing import List

import discord
from cogs.func import Context
from discord.errors import HTTPException, NotFound
from discord.ext import commands
from discord.message import Attachment, Message
from utils.config import ConfigMap
from utils.queue import BotQueue

LEAVE_AFTER_INACTIVITY_DELAY = 120
LEAVE_AFTER_INACTIVITY_DURATION = 600


class Bot(commands.Bot):
    def __init__(
        self, command_prefix, description, configmap: ConfigMap = None, dir="./uploads/"
    ):
        super().__init__(command_prefix=command_prefix, description=description)
        self.log = logging.getLogger("bot")
        self.dir = dir
        self.queue = BotQueue(self)
        self.config = configmap or ConfigMap(self, [])

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

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

                if not voice_client.is_playing():
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
                        voice_client.disconnect(), self.queue.deregister(id)
                    )
                    left.append(id)

            for id in left:
                del marked_for_inactivity[id]

            await asyncio.sleep(LEAVE_AFTER_INACTIVITY_DELAY)
