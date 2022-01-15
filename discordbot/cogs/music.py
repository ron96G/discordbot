import logging
from datetime import datetime

from discord.ext import commands
from discord.ext.commands.context import Context

from music_utils.spotify import Spotify
from music_utils.youtube import Youtube
from music_utils.ytdl import YTDLSource


class Music(commands.Cog):
    def __init__(
        self, bot: commands.Bot, youtube: Youtube = None, spotify: Spotify = None
    ):
        self.bot = bot
        self.log = logging.getLogger("cog")
        self.youtube = youtube
        self.spotify = spotify

    async def play_video(self, ctx: Context, query_or_url: str, stream=False):

        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        data = None
        async with ctx.typing():
            # convert query or spotify url to youtube url for streaming
            if self.spotify is not None and self.spotify.is_spotify_url_or_id(
                query_or_url
            ):
                params = await self.spotify.get_info(query_or_url)
                data = await self.youtube.find_video_by_query(
                    f'{params["artist"]} {params["name"]}'
                )
                url = data["url"]

            # convert query to a youtube url for streaming
            elif self.youtube is not None and not self.youtube.is_yt_url(query_or_url):
                data = await self.youtube.find_video_by_query(query_or_url)
                url = data["url"]

            # is already a valid youtube url
            else:
                url = query_or_url

            try:
                self.log.info(f'Trying to {"stream" if stream else "download"} {url}')
                _player = YTDLSource.from_url(url, loop=self.bot.loop, stream=stream)
            except Exception as e:
                self.log.error(e)
                raise commands.CommandError("failed to retrieve song")

            id = ctx.message.guild.id
            if not self.bot.queue.exists(id):
                await self.bot.queue.register(id)
            pos = await self.bot.queue.put(
                id, {"ctx": ctx, "player": _player, "time": datetime.now()}
            )
            return await ctx.message.reply(
                f'Queued {data["title"] + " " if data else ""}at position {pos}'
            )

    @commands.command()
    async def play(self, ctx: Context, *, query_or_url: str):
        """Play the provided query/url/song or add it to queue if one is already playing"""
        await self.play_video(ctx, query_or_url)

    @commands.command()
    async def stream(self, ctx: Context, *, query_or_url: str):
        """Play the provided query/url/song or add it to queue if one is already playing"""
        await self.play_video(ctx, query_or_url, True)

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Control the volume of the voice client"""
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")
