import logging
from random import randint

import discord
from common.context import Context
from discord.ext import commands


class Func(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger("cog")

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Ping the bot and check if it responds"""
        await ctx.send("pong")

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Command the bot to join the defined voice channel - if it exists"""
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command()
    async def summon(self, ctx):
        """Command the bot to join your voice channel - if you are connected to one"""
        await self.bot.join_author(ctx)

    @commands.command()
    async def guess(self, ctx: Context, number: int):
        """Guess a number between 1 and 6"""
        value = randint(1, 6)
        self.log.info(
            f'{ctx.author} guessed {"correct" if (number == value) else "incorrect"} ({number})'
        )
        await ctx.tick(number == value)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def whoami(self, ctx: Context):
        await ctx.send(f"You have all privileges {ctx.message.author.mention}")

    @whoami.error
    async def whoami_error(ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You have limited privileges {ctx.message.author.mention}")
