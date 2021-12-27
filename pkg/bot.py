import asyncio
import logging, os, mimetypes
from typing import List

from discord.errors import HTTPException, NotFound
from discord.ext import commands
from discord.message import Message, Attachment
from pkg.func import Context

from pkg.queue import BotQueue

class Bot(commands.Bot):
    def __init__(self, command_prefix, description, dir='./uploads/'):
        super().__init__(command_prefix = command_prefix, description = description)
        self.log = logging.getLogger('bot')
        self.dir = dir
        self.queue = BotQueue(self)

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    async def on_ready(self):
        self.log.info(f'Logged in as {self.user.name} with id {self.user.id}')

    async def get_context(self, message, *, cls=Context):
        return await super().get_context(message, cls=cls)

    async def on_message_delete(self, message: Message):
        self.log.info(f'message by {message.author} was deleted: {message.content}')

    async def on_message(self, message: Message):
        if message.author.id == self.user.id:
            return

        self.log.info(f'Received message from {message.author.display_name}: "{message.content}" with {len(message.attachments)} attachments')

        await self.process_commands(message)
        await self.handle_attachments(message.attachments)

    async def handle_attachments(self, attachments: List[Attachment]) -> None:
        if attachments is None:
            return 
        for a in attachments:
            output = os.path.join(self.dir, f'{a.id}{mimetypes.guess_extension(a.content_type)}')
            try:
                await a.save(output)
            except (HTTPException, NotFound) as e:
                raise commands.CommandError('unable to handle attachment', e)
  
    async def join_author(self, ctx: commands.Context):
        if ctx.author.voice:
            if ctx.voice_client is not None:
                return await ctx.voice_client.move_to(ctx.author.voice.channel)
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You are not connected to a voice channel")
            raise commands.CommandError("user is not connected to a voice channel")
