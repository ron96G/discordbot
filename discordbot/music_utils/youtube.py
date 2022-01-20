import logging
import re
from typing import Dict

from googleapiclient.errors import HttpError

YOUTUBE_VIDEO_BASE_URL = "https://www.youtube.com/watch?v="
YOUTUBE_VIDEO_ID_REGEX = re.compile(r"^.*v=([^&]*).*$")
YOUTUBE_PLAYLIST_ID_REGEX = re.compile(r"^.*list=([^&]*).*$")


class YouTubeError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


class Youtube:
    def __init__(self, service):
        self.service = service
        self.log = logging.getLogger("svc")

    def __del__(self):
        self.service.close()

    def is_yt_url(self, url: str) -> bool:
        return "youtube" in url

    # Unused
    def url_to_playlist_id(self, url: str) -> str:
        found_id = YOUTUBE_PLAYLIST_ID_REGEX.search(url)
        if found_id:
            return found_id.group(1)
        return ""

    def url_to_video_id(self, url: str) -> str:
        found_id = YOUTUBE_VIDEO_ID_REGEX.search(url)
        if found_id:
            return found_id.group(1)
        return ""

    async def find_video_by_url(self, url: str) -> Dict[str, str]:

        id = self.url_to_video_id(url)
        if id == "":
            raise Exception("Invalid youtube url")

        req = self.service.videos().list(
            id=id,
            part="id,snippet",
            maxResults=1,
        )

        self.log.info(f'Searching youtube for "{id}"')

        return await self.__run_req_for_video_info(req)

    async def find_video_by_query(self, query: str) -> Dict[str, str]:
        req = self.service.search().list(
            part="id,snippet",
            fields="items(id(videoId),snippet(title))",
            type="video",
            q=query,
            maxResults=1,
        )
        self.log.info(f'Searching youtube for "{query}"')

        return await self.__run_req_for_video_info(req)

    async def __run_req_for_video_info(self, req) -> Dict[str, str]:
        try:
            res = req.execute()

            if len(res["items"]) > 0:
                id_item = res["items"][0]["id"]
                id = id_item["videoId"] if isinstance(id_item, dict) else id_item
                return {
                    "url": YOUTUBE_VIDEO_BASE_URL + id,
                    "title": res["items"][0]["snippet"]["title"],
                    "thumbnail": f"https://img.youtube.com/vi/{id}/hqdefault.jpg",
                }

        except HttpError as e:
            self.log.error(
                f"failed to fetch videos failed with {e.status_code}: {e.error_details}"
            )
            raise YouTubeError("Failed to fetch videos", e)

        return {
            "url": YOUTUBE_VIDEO_BASE_URL + "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
            "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        }
