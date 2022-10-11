from typing import List

from common.context import Context

from ..track import Track, TrackInfo


class YoutubeTrackInfo(TrackInfo):
    def __init__(self, url: str, title: str, thumbnail_url: str, download_url: str):
        super().__init__(url, title, thumbnail_url, download_url)

    def pretty_print(self):
        return f'TrackInfo: "{self.title}" ({self.url})'


class YoutubeTrack(Track):
    def __init__(self, ctx: Context, info: List[TrackInfo], volume=0.5):
        super().__init__(ctx, info, volume)
