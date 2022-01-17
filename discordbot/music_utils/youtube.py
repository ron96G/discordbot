import logging

from googleapiclient.errors import HttpError

YOUTUBE_VIDEO_BASE_URL = "https://www.youtube.com/watch?v="


class Youtube:
    def __init__(self, service):
        self.service = service
        self.log = logging.getLogger("svc")

    def __del__(self):
        self.service.close()

    def is_yt_url(self, url: str) -> bool:
        return "youtube" in url

    async def find_video_by_query(self, query: str) -> str:
        req = self.service.search().list(
            part="id,snippet",
            fields="items(id(videoId),snippet(publishedAt,channelId,channelTitle,title,description))",
            type="video",
            q=query,
            maxResults=1,
        )
        self.log.info(f'Searching youtube for "{query}"')

        try:
            res = req.execute()
            if len(res["items"]) > 0:
                id = res["items"][0]["id"]["videoId"]
                return {
                    "url": YOUTUBE_VIDEO_BASE_URL + id,
                    "title": res["items"][0]["snippet"]["title"],
                    "thumbnail": f"https://img.youtube.com/vi/{id}/hqdefault.jpg",
                }

        except HttpError as e:
            self.log.error(
                f"failed to fetch videos failed with {e.status_code}: {e.error_details}"
            )
            # TODO raise exception

        return {
            "url": YOUTUBE_VIDEO_BASE_URL + "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
            "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        }
