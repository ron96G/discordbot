
from datetime import datetime
import logging
from discord.errors import DiscordException
from discord.ext.commands.context import Context
from discord.ext import commands

from pkg.music_utils.spotify import Spotify
from pkg.music_utils.youtube import Youtube
from pkg.music_utils.ytdl import YTDLSource

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot, youtube: Youtube = None, spotify: Spotify = None):
        self.bot = bot
        self.log = logging.getLogger('cog')
        self.youtube = youtube
        self.spotify = spotify
    
    async def play_video(self, ctx: Context, query_or_url: str, stream = False):
        
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)
        
        async with ctx.typing():
            # convert query or spotify url to youtube url for streaming
            if self.spotify is not None and self.spotify.is_spotify_url_or_id(query_or_url):
                params = await self.spotify.get_info(query_or_url)
                url = await self.youtube.find_video_by_query(f'{params["artist"]} {params["name"]}')

            # convert query to a youtube url for streaming
            elif self.youtube is not None and not self.youtube.is_yt_url(query_or_url):
                url = await self.youtube.find_video_by_query(query_or_url)
        
            # is already a valid youtube url
            else:
                url = query_or_url

            try:
                self.log.info(f'Trying to {"stream" if stream else "download"} {url}')
                _player = YTDLSource.from_url(url, loop=self.bot.loop, stream=stream)
            except Exception as e:
                self.log.error(e)
                raise commands.CommandError('failed to retrieve song')

            if ctx.voice_client.is_playing():
                id = ctx.message.guild.id
                if not self.bot.queue.exists(id):
                    self.bot.queue.register(id)
                pos = await self.bot.queue.put(id, {'ctx': ctx, 'player': _player, 'time': datetime.now()})
                return await ctx.message.reply(f'Queued at position {pos}')

            
            try:
                player = await _player
                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            except DiscordException as e:
                self.log.error(f'Failed to play audio: {e}')
                await ctx.send(f'Failed to play {player.title}. Skipping...')
            else:
                await ctx.send(f'Now playing: {player.title}')


    @commands.command()
    async def play(self, ctx: Context, *, query_or_url: str):
        await self.play_video(ctx, query_or_url)

    @commands.command()
    async def stream(self, ctx: Context, *, query_or_url: str):
        await self.play_video(ctx, query_or_url, True)

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")