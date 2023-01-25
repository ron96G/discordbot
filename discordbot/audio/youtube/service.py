import logging
import os
import re
from typing import List

import yt_dlp
from googleapiclient.errors import HttpError

from .track import YoutubeTrackInfo

YOUTUBE_VIDEO_BASE_URL = "https://www.youtube.com/watch?v="
YOUTUBE_VIDEO_ID_REGEX = re.compile(r"^.*v=([^&]*).*$")
YOUTUBE_PLAYLIST_ID_REGEX = re.compile(r"^.*list=([^&]*).*$")

YTDL_OUTPUT_DIR = "./ytdl"
YTDL_FORMAT_OPTS = {
    "format": "bestaudio/best",
    "outtmpl": YTDL_OUTPUT_DIR + "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": False,
    "verbose": True,
    "no_warnings": False,
    "fixup": "detect_or_warn",
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
    "cachedir": False,
    "keepvideo": False,
}


def set_additional_ytdl_opts(*opts: str):
    ydtl_opts = YTDL_FORMAT_OPTS.copy()
    if len(opts) % 2 != 0:
        raise YouTubeError("Invalid number of argument for ytdl opts extension")

    for i in range(0, len(opts), 2):
        ydtl_opts[opts[i]] = opts[i + 1]

    return ydtl_opts


class YouTubeError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


class YoutubeService:

    log = logging.getLogger("svc")

    def __init__(self, service, ytdl_opts=None):
        self.service = service
        self.ytdl = yt_dlp.YoutubeDL(ytdl_opts or YTDL_FORMAT_OPTS)

    @classmethod
    def new_with_credentials(cls, service, username: str, password: str):
        ytdl_opts = set_additional_ytdl_opts("username", username, "password", password)
        return cls(service, ytdl_opts)

    def __del__(self):
        self.service.close()

    def is_yt_url(self, url: str) -> bool:
        return "youtube" in url

    def is_yt_playlist_url(self, url: str) -> bool:
        return "youtube" in url and "list" in url

    def url_to_video_id(self, url: str) -> str:
        found_id = YOUTUBE_VIDEO_ID_REGEX.search(url)
        if found_id:
            return found_id.group(1)
        return None

    def url_to_playlist_id(self, url: str) -> str:
        found_id = YOUTUBE_PLAYLIST_ID_REGEX.search(url)
        if found_id:
            return found_id.group(1)
        return None

    async def get_playlist_info(
        self, id: str, max_entries=20
    ) -> List[YoutubeTrackInfo]:
        req = self.service.playlistItems().list(
            playlistId=id,
            part="id,snippet",
            fields="items(snippet(title,thumbnails(medium),resourceId(videoId)))",
            maxResults=max_entries,
        )
        return await self._fetch_video_info(req)

    async def get_video_info(self, id: str) -> List[YoutubeTrackInfo]:
        self.log.info(f'Getting video info for id "{id}"')
        req = self.service.videos().list(
            id=id,
            part="id,snippet",
            fields="items(id,snippet(title,thumbnails(medium)))",
            maxResults=1,
        )
        return await self._fetch_video_info(req)

    async def get_video_info_by_query(self, query: str) -> List[YoutubeTrackInfo]:
        self.log.info(f'Getting video info for query "{query}"')
        req = self.service.search().list(
            part="id,snippet",
            fields="items(id,snippet(title,thumbnails(medium)))",
            type="video",
            q=query,
            maxResults=1,
        )
        return await self._fetch_video_info(req)

    async def get_info(self, url: str) -> List[YoutubeTrackInfo]:
        if self.is_yt_playlist_url(url):
            id = self.url_to_playlist_id(url)
            return await self.get_playlist_info(id)

        elif self.is_yt_url(url):
            id = self.url_to_video_id(url)
        else:
            raise YouTubeError(f"Invalid input {url}")

        return await self.get_video_info(id)

    async def get_download_url(self, info: YoutubeTrackInfo, stream=True):
        return await self._extract_info(info, stream=stream)

    async def _extract_info(
        self, info: YoutubeTrackInfo, stream=True, max_entries=1, cur_try=0, max_try=3
    ) -> List[YoutubeTrackInfo]:
        self.log.warn("Sending request via YTDL")
        try:
            cur_try += 1
            data = self.ytdl.extract_info(info.url, download=not stream)
            info_list: List[YoutubeTrackInfo] = []

            self.log.debug(data)

            if "entries" in data:
                for data in data["entries"]:
                    if len(info_list) >= max_entries:
                        break
                    download_url = (
                        data["url"] if stream else self.ytdl.prepare_filename(data)
                    )
                    info_list.append(
                        YoutubeTrackInfo(
                            info.url, info.title, info.thumbnail, download_url
                        )
                    )

            else:
                download_url = (
                    data["url"] if stream else self.ytdl.prepare_filename(data)
                )
                info_list.append(
                    YoutubeTrackInfo(info.url, info.title, info.thumbnail, download_url)
                )
            return info_list
        except Exception as e:
            if cur_try >= max_try:
                self.log.warn("Failed to extract youtube info. Retrying...", e)
                return self._extract_info(info, stream, max_entries, cur_try, max_try)
            else:
                self.log.error(
                    "Failed to extract youtube info. Exceeded retry limit", e
                )
                raise e

    async def _fetch_video_info(self, req) -> List[YoutubeTrackInfo]:
        info_list = []
        try:
            self.log.warn("Sending request to Youtube API")
            res = req.execute()
            self.log.debug(res)

            for item in res["items"]:
                self.log.info(f"Received video info from youtube: {item}")
                if "resourceId" in item["snippet"]:
                    id = item["snippet"]["resourceId"]["videoId"]
                else:
                    id = item["id"]

                if isinstance(id, dict):
                    id = id["videoId"]

                info = YoutubeTrackInfo(
                    YOUTUBE_VIDEO_BASE_URL + id,
                    item["snippet"]["title"],
                    item["snippet"]["thumbnails"]["medium"]["url"],
                    "",
                )
                self.log.info(f"Constructed track info: {info}")
                info_list.append(info)

        except HttpError as e:
            self.log.error(
                f"failed to fetch videos failed with {e.status_code}: {e.error_details}"
            )
            raise YouTubeError(f"Failed to fetch videos: {e.error_details}", e)

        except Exception as e:
            self.log.error(f"failed to fetch videos failed with {e}")
            raise YouTubeError("Failed to fetch videos", e)

        return info_list
