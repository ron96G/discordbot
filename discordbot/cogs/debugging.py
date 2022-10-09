import logging
from dataclasses import dataclass
from queue import PriorityQueue
from typing import Dict, List, Optional

import music_utils
import youtube_dl
from cogs.func import Context
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.embeds import Embed
from discord.ext import commands
from discord.voice_client import VoiceClient

YTDL_OUTPUT_DIR = "./ytdl"

YTDL_FORMAT_OPTS = {
    "format": "bestaudio/best",
    "outtmpl": YTDL_OUTPUT_DIR + "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}


FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = youtube_dl.YoutubeDL(YTDL_FORMAT_OPTS)


@dataclass
class TrackInfo:
    url: str
    title: str
    thumbnail: Optional[str] = ""
    download_url: Optional[str] = ""


class Track:
    info: List[TrackInfo]
    _player: PCMVolumeTransformer
    current = 0
    length = 0
    volume: float

    def __init__(self, info: List[TrackInfo], volume=0.5):
        if isinstance(info, list):
            self.info = info
        else:
            self.info = [info]

        self.length = len(self.info)
        self.current = 0
        self._player = None
        self.volume = volume

    def __len__(self):
        return self.length - self.current

    def __del__(self):
        print(f"Deleting track {self.info}")

    def _build_player(self, download_url: str):
        return PCMVolumeTransformer(
            FFmpegPCMAudio(download_url, **FFMPEG_OPTS), self.volume
        )

    # get the info about the currently active track
    def get_current_info(self) -> TrackInfo:
        if self.current == 0:
            raise ValueError("There is no active track. Select the next first.")
        return self.info[self.current - 1]

    def isMultipleTracks(self):
        return self.length > 1

    def hasNext(self):
        return self.current < self.length

    def next(self):
        if not self.hasNext():
            return None

        track = self.info[self.current]
        print(f"Building player for {track}")
        self._player = self._build_player(track.download_url)
        self.current += 1
        return self._player


class TrackQueue:
    log = logging.getLogger("track_queue")
    queue: Dict[str, PriorityQueue]
    maxsize: int

    def __init__(self, maxsize=20):
        self.maxsize = maxsize
        self.queue = {}

    def __len__(self):
        return len(self.queue)

    def has(self, id: str):
        return self.queue.get(id) is not None

    def new(self, id: str):
        if self.has(id):
            raise ValueError(f"{id} already exists")
        else:
            self.queue[id] = PriorityQueue(self.maxsize)
        return self.queue[id]

    def put(self, id: str, tracks: List[Track], prio=999):
        if not isinstance(tracks, list):
            tracks = [tracks]
        queue = self.queue.get(id)
        if queue is None:
            queue = self.new(id)

        try:
            for track in tracks:
                queue.put_nowait((prio, track))

        except Exception as e:
            raise ValueError(e)

    def put_back(self, id: str, tracks: List[Track]):
        self.put(id, tracks, 900)

    def get(self, id: str) -> Track:
        queue = self.queue.get(id)
        if queue is None:
            raise ValueError(f"Queue for {id} does not exist")
        else:
            return queue.get(block=True, timeout=None)[1]


def get_voice_client(voice_clients: List[VoiceClient], guild_id: str) -> VoiceClient:
    for c in voice_clients:
        if c.guild.id == guild_id:
            return c
    return None


def extract_embedded_info(ctx: Context) -> TrackInfo:
    embeds: List[Embed] = ctx.message.embeds
    if bool(embeds):
        return TrackInfo(embeds[0].url, embeds[0].title, embeds[0].thumbnail.url)


def extract_info_from_youtube(url: str, stream=True, max_entries=1) -> List[TrackInfo]:
    data = ytdl.extract_info(url, download=not stream)
    info_list = []
    if "entries" in data:
        for data in data["entries"]:
            if len(info_list) >= max_entries:
                break

            download_url = data["url"] if stream else ytdl.prepare_filename(data)
            info_list.append(TrackInfo(download_url, "", "", download_url))

    else:
        download_url = data["url"] if stream else ytdl.prepare_filename(data)
        info_list.append(TrackInfo(download_url, "", "", download_url))

    return info_list


class Debugging(commands.Cog):
    log = logging.getLogger("cog")

    def __init__(
        self,
        bot: commands.Bot,
        youtube: music_utils.Youtube = None,
        spotify: music_utils.Spotify = None,
        twitch: music_utils.Twitch = None,
    ):
        self.bot = bot
        self.youtube = youtube
        self.spotify = spotify
        self.twitch = twitch

        self.queue = TrackQueue()

    @commands.command()
    async def v2_stream(self, ctx: Context, *, query_or_url: str):
        """V2 Debugging Command"""

        guild_id = ctx.guild.id
        if ctx.voice_client is None:
            await self.bot.join_author(ctx)

        voice = get_voice_client(self.bot.voice_clients, guild_id) or ctx.voice_client
        info = extract_embedded_info(ctx)

        try:
            if self.twitch.is_twitch_url(query_or_url):
                self.log.info("input is a twitch url")
                download_url = self.twitch._get_direct_stream_link(query_or_url)
                self.log.debug(f"download_url={download_url}")
                info.download_url = download_url

                track = Track(info)

            elif self.spotify.is_spotify_url(query_or_url):
                self.log.info("input is a spotify url")
                spotify_info_list = await self.spotify.get_info(query_or_url)
                playlist_info = []
                for spotify_info in spotify_info_list:
                    youtube_info = await self.youtube.find_video_by_query(
                        f"{spotify_info['artist']} - {spotify_info['name']}"
                    )
                    self.log.debug(youtube_info)
                    download_url = extract_info_from_youtube(youtube_info["url"])[
                        0
                    ].download_url

                    playlist_info.append(
                        TrackInfo(
                            youtube_info["url"],
                            youtube_info["title"],
                            spotify_info["thumbnail"],
                            download_url,
                        )
                    )

                track = Track(playlist_info)

            elif self.youtube.is_yt_url(query_or_url):
                self.log.info("input is a youtube url")
                youtube_info = await self.youtube.find_video_by_url(query_or_url)
                self.log.debug(youtube_info)

                download_url = extract_info_from_youtube(youtube_info["url"])[
                    0
                ].download_url
                self.log.debug(f"download_url={download_url}")
                if info is None:
                    info = TrackInfo(
                        youtube_info["url"],
                        youtube_info["title"],
                        youtube_info["thumbnail"],
                    )

                track = Track(info)

            else:
                self.log.info("input is a query")
                youtube_info = await self.youtube.find_video_by_query(query_or_url)
                self.log.debug(youtube_info)

                download_url = extract_info_from_youtube(youtube_info["url"])[
                    0
                ].download_url
                self.log.debug(f"download_url={download_url}")
                if info is None:
                    info = TrackInfo(
                        youtube_info["url"],
                        youtube_info["title"],
                        youtube_info["thumbnail"],
                    )

                track = Track(info)

        except Exception as e:
            self.log.error(e)
            print(e.__cause__)
            await ctx.reply_formatted_error(e, "Internal Server Error")

        else:
            id = ctx.guild.id

            info.download_url = download_url

            self.queue.put(id, track)

            track = self.queue.get(id)
            print(len(track))
            voice.play(track.next(), after=lambda e: print(e))

            if track.hasNext():
                self.queue.put_back(id, track)

            info = track.get_current_info()

            await ctx.reply_formatted_msg(
                f"Now playing {info.title}", thumbnail_url=info.thumbnail
            )

    @commands.command()
    async def v2_play(self, ctx: Context, *, query_or_url: str):
        """V2 Debugging Command"""

        await ctx.reply_formatted_error(
            "v2_play is not implemented.", "Not Implemented"
        )
