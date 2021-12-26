import logging, os, asyncio, youtube_dl
from discord.ext.commands.context import Context

import discord
from discord.ext import commands

from googleapiclient.errors import HttpError

YOUTUBE_VIDEO_BASE_URL = 'https://www.youtube.com/watch?v='
YTDL_OUTPUT_DIR = './ytdl/'

if not os.path.exists(YTDL_OUTPUT_DIR):
    os.makedirs(YTDL_OUTPUT_DIR)

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ffmpeg_options = {
    'options': '-vn'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': YTDL_OUTPUT_DIR + '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

def is_valid_url(url: str) -> bool:
    return url.startswith("https://")

class Youtube():
    def __init__(self, service):
        self.service = service
        self.log = logging.getLogger('cog')

    async def find_video_by_query(self, query: str) -> str:
        req = self.service.search().list(
            part="id,snippet",
            fields="items(id(videoId),snippet(publishedAt,channelId,channelTitle,title,description))",
            type='video',
            q=query,
            maxResults=1,
        )
        
        try:
            res = req.execute()
            self.log.debug(res)
            return YOUTUBE_VIDEO_BASE_URL + res["items"][0]["id"]["videoId"]

        except HttpError as e:
            self.log.error(f'failed to fetch videos failed with {e.status_code}: {e.error_details}')
            # TODO raise exception

        return YOUTUBE_VIDEO_BASE_URL + 'dQw4w9WgXcQ'

# Copied from https://github.com/Rapptz/discord.py/blob/45d498c1b76deaf3b394d17ccf56112fa691d160/examples/basic_voice.py#L33    
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot, youtube: Youtube = None):
        self.bot = bot
        self.youtube = youtube
    
    async def play_video(self, ctx: Context, query_or_url: str, stream = False):
        
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)
        
        if self.youtube is not None and not is_valid_url(query_or_url):
            url = await self.youtube.find_video_by_query(query_or_url)
        else:
            url = query_or_url

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=stream)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

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