import logging
from random import randint

import discord
from discord.ext import commands

class Context(commands.Context):
     async def tick(self, value):
        emoji = '\N{WHITE HEAVY CHECK MARK}' if value else '\N{CROSS MARK}'
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

class Func(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger('cog')

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send('pong')

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command()
    async def summon(self, ctx):
        await self.bot.join_author(ctx)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if ctx.voice_client is not None:
            ctx.voice_client.pause()

    @commands.command()
    async def skip(self, ctx: Context):
        if ctx.voice_client is not None:
            ctx.voice_client.stop()

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if ctx.voice_client is not None:
            ctx.voice_client.resume()

    @commands.command()
    async def guess(self, ctx: Context, number: int):
        value = randint(1, 6)
        self.log.info(f'{ctx.author} guessed {"correct" if (number == value) else "incorrect"} ({number})')
        await ctx.tick(number == value)

    @commands.command()
    async def clear(self, ctx: commands.Context):
        n = await self.bot.queue.clear(ctx.message.guild.id)
        await ctx.send(f'Successfully cleared queue with {n} items.')

    @commands.command()
    async def size(self, ctx: commands.Context):
        n = self.bot.queue.size(ctx.message.guild.id)
        await ctx.send(f'Currently there are {n} items queued.')