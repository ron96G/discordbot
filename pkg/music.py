import logging, os, asyncio, youtube_dl, re, requests
from discord.ext.commands.context import Context

import discord
from discord.ext import commands

import spotipy

from googleapiclient.errors import HttpError

YOUTUBE_VIDEO_BASE_URL = 'https://www.youtube.com/watch?v='
SPOTIFY_MARKET = "DE"
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


class Spotify():
    def __init__(self, service: spotipy.Spotify):
        self.service = service
        self.log = logging.getLogger('svc')
        self.id_re = re.compile(r'^[A-Za-z0-9]{22}$')

    def __del__(self):
        pass
    
    def is_spotify_url_or_id(self, url_or_id: str) -> bool:
        is_url = 'spotify' in url_or_id
        is_id =  bool(self.id_re.match(url_or_id))
        return is_url | is_id

    async def get_info(self, id_or_url: str):
        self.log.info(f'Searching spotify for "{id_or_url}"')
        track = self.service.track(id_or_url, market=SPOTIFY_MARKET)

        self.log.debug(track)

        return {
            'artist': track['artists'][0]['name'],
            'name': track['name']
        }

class Youtube():
    def __init__(self, service):
        self.service = service
        self.log = logging.getLogger('svc')
    
    def __del__(self):
        self.service.close()

    def is_yt_url(self, url: str) -> bool:
        return 'youtube' in url

    async def find_video_by_query(self, query: str) -> str:
        req = self.service.search().list(
            part="id,snippet",
            fields="items(id(videoId),snippet(publishedAt,channelId,channelTitle,title,description))",
            type='video',
            q=query,
            maxResults=1,
        )
        self.log.info(f'Searching youtube for "{query}"')

        try:
            res = req.execute()
            if len(res["items"]) > 0:
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
    def __init__(self, bot: commands.Bot, youtube: Youtube = None, spotify: Spotify = None):
        self.bot = bot
        self.youtube = youtube
        self.spotify = spotify
    
    async def play_video(self, ctx: Context, query_or_url: str, stream = False):
        
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)
        
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