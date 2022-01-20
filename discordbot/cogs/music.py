import logging
from datetime import datetime
from typing import Dict

import music_utils
from cogs.func import Context
from discord.ext import commands


class Music(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        youtube: music_utils.Youtube = None,
        spotify: music_utils.Spotify = None,
    ):
        self.bot = bot
        self.log = logging.getLogger("cog")
        self.youtube = youtube
        self.spotify = spotify

    async def enqueue_track(
        self, ctx: Context, data: Dict[str, str], stream: bool = True
    ) -> int:

        url = data["url"]
        try:
            self.log.info(f'Trying to {"stream" if stream else "download"} {url}')
            _player = music_utils.YTDLSource.from_url(
                url, loop=self.bot.loop, stream=stream
            )

        except Exception as e:
            self.log.warn(f'Failed to retrieve song "{url}": {e}')
            raise commands.CommandError("failed to retrieve song")

        id = ctx.message.guild.id
        if not self.bot.queue.exists(id):
            await self.bot.queue.register(id)
        pos = await self.bot.queue.put(
            id,
            {
                "ctx": ctx,
                "player": _player,
                "time": datetime.now(),
                "thumbnail": data["thumbnail"] if "thumbnail" in data else None,
            },
        )
        return pos

    async def play_tracks(self, ctx: Context, query_or_url: str, stream: bool = True):

        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        data = []
        async with ctx.typing():
            self.log.info(f"Checking if {query_or_url} is a youtube url")

            # convert query or spotify url to youtube url for streaming
            if self.spotify is not None and self.spotify.is_spotify_url(query_or_url):
                self.log.info(f"{query_or_url} is a spotify url")
                try:
                    if stream and (
                        self.spotify.is_spotify_album(query_or_url)
                        or self.spotify.is_spotify_playlist(query_or_url)
                    ):
                        self.log.info(
                            'Albums and playlists are only supported in "play" mode'
                        )
                        return await ctx.reply_formatted_error(
                            f'Albums and playlists are only supported in "play" mode'
                        )

                    tracks = await self.spotify.get_info(query_or_url)
                    self.log.info(f"Found {len(tracks)} tracks")

                    for track in tracks:
                        _data = await self.youtube.find_video_by_query(
                            f'{track["artist"]} {track["name"]}'
                        )
                        _data["thumbnail"] = track["thumbnail"]

                        data.append(_data)

                except music_utils.SpotifyError as e:
                    self.log.warn(f"Failed to get spotify info: {e}")
                    return await ctx.reply_formatted_error(
                        f'Failed to play "{query_or_url}": {e}'
                    )

                except music_utils.YouTubeError as e:
                    self.log.warn(f"Failed to get youtube info: {e}")
                    return await ctx.reply_formatted_error(
                        f'Failed to play "{query_or_url}": {e}'
                    )

            # convert query to a youtube url for streaming
            elif self.youtube is not None and not self.youtube.is_yt_url(query_or_url):
                self.log.info(f"{query_or_url} is a query")
                try:
                    data.append(await self.youtube.find_video_by_query(query_or_url))

                except music_utils.YouTubeError as e:
                    self.log.warn(f"Failed to get youtube info: {e}")
                    return await ctx.reply_formatted_error(
                        f'Failed to play "{query_or_url}": {e}'
                    )

            # is already a valid youtube url
            elif self.youtube is not None and self.youtube.is_yt_url(query_or_url):
                self.log.info(f"{query_or_url} is a youtube url")
                try:
                    data.append(await self.youtube.find_video_by_url(query_or_url))

                except music_utils.YouTubeError as e:
                    self.log.warn(e)
                    return await ctx.reply_formatted_error(
                        f'Failed to play "{query_or_url}": {e}'
                    )

            else:
                self.log.warn(f"{query_or_url} is not known")
                raise commands.CommandError("Unknown query or url")

            # append all videos to queue
            for _data in data:
                pos = await self.enqueue_track(ctx, _data, stream)

            await ctx.tick(True)

            if len(data) > 1:
                return await ctx.reply_formatted_msg(f"Queued {len(data)} songs")

    @commands.command()
    async def play(self, ctx: Context, *, query_or_url: str):
        """Play the provided query/url/song or add it to queue if one is already playing"""
        await self.play_tracks(ctx, query_or_url, False)

    @commands.command()
    async def stream(self, ctx: Context, *, query_or_url: str):
        """Play the provided query/url/song or add it to queue if one is already playing"""
        await self.play_tracks(ctx, query_or_url, True)

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Control the volume of the voice client"""
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")
