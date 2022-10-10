from typing import List

from common.context import Context

from ..track import Track, TrackInfo


class SpotifyTrackInfo(TrackInfo):
    artist: str
    name: str

    def __init__(self, url: str, artist: str, name: str, thumbnail_url: str):
        super().__init__(url, f"{artist} - {name}", thumbnail_url)
        self.artist = artist
        self.name = name


class SpotifyTrack(Track):
    def __init__(self, ctx: Context, info: List[TrackInfo], volume=0.5):
        super().__init__(ctx, info, volume)
