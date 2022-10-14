import logging
from typing import List

from audio import (
    LinksService,
    SpotifyService,
    SpotifyTrackInfo,
    Track,
    TrackInfo,
    YoutubeService,
    YoutubeTrackInfo,
)
from cogs import Context
from common.context import Context
from discord.embeds import Embed
from discord.ext import commands


def extract_embedded_info(ctx: Context) -> TrackInfo:
    embeds: List[Embed] = ctx.message.embeds
    if bool(embeds):
        return TrackInfo(embeds[0].url, embeds[0].title, embeds[0].thumbnail.url)


class Music(commands.Cog):
    log = logging.getLogger("cog")

    def __init__(
        self,
        bot: commands.Bot,
        youtube: YoutubeService = None,
        spotify: SpotifyService = None,
        links: LinksService = None,
    ):
        self.bot = bot
        self.youtube = youtube
        self.spotify = spotify
        self.links = links

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Control the volume of the voice client"""
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def play(self, ctx: Context, *, query_or_url: str):
        """Not implemented"""

        await ctx.reply_formatted_error("play is not implemented.", "Not Implemented")

    @commands.command()
    async def stream(self, ctx: Context, *, query_or_url: str):
        """Stream videos, songs, albums and playlists from various sources like YouTube, Spotify, Twitch, ..."""

        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        async with ctx.typing():
            info = extract_embedded_info(ctx)

            try:
                if self.spotify.is_spotify_url(query_or_url):
                    self.log.info("input is a spotify url")
                    spotify_info_list = await self.spotify.get_info(query_or_url)

                    track = Track(ctx, spotify_info_list)

                    async def fetch_download_url(track_info: SpotifyTrackInfo):
                        self.log.debug(f"Running before_build: {track_info}")
                        youtube_info = (
                            await self.youtube.get_video_info_by_query(
                                f"{track_info.artist} - {track_info.name}"
                            )
                        )[0]
                        youtube_download_info = (
                            await self.youtube.get_download_url(youtube_info, True)
                        )[0]

                        track_info.title = youtube_info.title
                        track_info.download_url = youtube_download_info.download_url
                        track_info.thumbnail = youtube_info.thumbnail

                    track.set_before_build(fetch_download_url)

                elif self.youtube.is_yt_url(query_or_url):
                    self.log.info("input is a youtube url")

                    if self.youtube.is_yt_playlist_url(query_or_url) or info is None:
                        self.log.info(
                            "embedded info is insufficient. Fetching info from Youtube."
                        )
                        info = await self.youtube.get_info(query_or_url)
                    else:
                        info.url = query_or_url

                    track = Track(ctx, info)

                    async def fetch_download_url(track_info: YoutubeTrackInfo):
                        self.log.debug(f"Running before_build: {track_info}")
                        youtube_info = (
                            await self.youtube.get_download_url(track_info, True)
                        )[0]
                        track_info.title = youtube_info.title
                        track_info.download_url = youtube_info.download_url
                        track_info.thumbnail = youtube_info.thumbnail

                    track.set_before_build(fetch_download_url)

                elif self.links.is_url(query_or_url):
                    self.log.info("input is a url")
                    stream_url = self.links.find_stream(query_or_url)
                    if info is None:
                        info = TrackInfo(
                            query_or_url,
                            "Stream",
                            None,
                            "",
                        )
                    info.download_url = stream_url
                    track = Track(ctx, info)

                else:
                    self.log.info("input is a query")
                    youtube_info = (
                        await self.youtube.get_video_info_by_query(query_or_url)
                    )[0]
                    youtube_download_info = await self.youtube.get_download_url(
                        youtube_info
                    )
                    track = Track(ctx, youtube_download_info)

            except Exception as e:
                self.log.error(e)
                return await ctx.reply_formatted_error(e, "Error")

            id = ctx.guild.id

            if not self.bot.queue.has(id):
                self.bot.runner.register(id)

            tracks_count = len(track)
            self.log.info(f"Trying to enqueue {tracks_count} track(s) for {id}")
            await self.bot.queue.put(id, track)
            self.log.info(f"Successfully enqueued {tracks_count} track(s) for {id}")

            if tracks_count > 1:
                await ctx.reply_formatted_msg(
                    f"Successfully enqueued {tracks_count} tracks."
                )
            else:
                await ctx.tick("OK")
