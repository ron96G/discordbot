import asyncio
import logging
import os
from typing import Dict, Union

import discord
import youtube_dl
from youtube_dl.utils import DownloadError, ExtractorError, YoutubeDLError

YTDL_OUTPUT_DIR = "./ytdl/"

if not os.path.exists(YTDL_OUTPUT_DIR):
    os.makedirs(YTDL_OUTPUT_DIR)

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

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

# Based on https://github.com/Rapptz/discord.py/blob/45d498c1b76deaf3b394d17ccf56112fa691d160/examples/basic_voice.py#L33
class YTDLSource(discord.PCMVolumeTransformer):

    title: str
    url: str
    data: dict
    error: Union[YoutubeDLError, str, None]

    def __init__(
        self,
        original,
        *,
        data: Dict[str, str],
        error: YoutubeDLError = None,
        volume=0.5,
    ):

        self.log = logging.getLogger("ytdl_source")
        if error is not None:
            self.log.warn(f"Unable to construct audiosource: {repr(error)}")
            if isinstance(error, DownloadError):
                self.error = error.exc_info[1]

        else:
            super().__init__(original, volume)
            self.data = data
            self.title = data.get("title")
            self.url = data.get("url")
            self.error = None
            self.log.info(f'Successfully constructed audiosource for "{self.title}"')

    @classmethod
    def _from_url(cls, url, *, stream=False):
        try:
            data = ytdl.extract_info(url, download=not stream)
            if "entries" in data:
                # take first item from a playlist
                data = data["entries"][0]

            filename = data["url"] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTS), data=data)

        except DownloadError as e:
            return cls(None, data={}, error=e)

        except YoutubeDLError as e:
            return cls(None, data={}, error=e)

    @classmethod
    def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        return loop.run_in_executor(
            None, lambda: YTDLSource._from_url(url=url, stream=stream)
        )


def format_exception(e: Exception) -> Union[str, Exception]:
    return str(e).replace("\n", ". ")
