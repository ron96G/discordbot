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
    async def stop(self, ctx: commands.Context):
        """Command the bot to disconnect from the voice channel"""
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx: commands.Context):
        """Pause the currently playing audio source - may be resumed later"""
        if ctx.voice_client is not None:
            ctx.voice_client.pause()

    @commands.command()
    async def skip(self, ctx: Context):
        """Skip either the currently playing song or the next queued one if none is playing"""
        async with ctx.typing():
            if ctx.voice_client is not None and ctx.voice_client.is_playing():
                # skip the song that the voice_client is currently playing
                ctx.voice_client.stop()
            else:
                # skip the first track that is queued if no song is currently playing
                await self.pop(ctx)

    @commands.command()
    async def resume(self, ctx: commands.Context):
        """Resume the audio source playback"""
        if ctx.voice_client is not None:
            ctx.voice_client.resume()

    @commands.command()
    async def guess(self, ctx: Context, number: int):
        """Guess a number between 1 and 6"""
        value = randint(1, 6)
        self.log.info(
            f'{ctx.author} guessed {"correct" if (number == value) else "incorrect"} ({number})'
        )
        await ctx.tick(number == value)

    @commands.command()
    async def pop(self, ctx: Context):
        """Remove the next track from the queue"""
        self.bot.queue.pop(ctx.message.guild.id)
        await ctx.tick(True)
