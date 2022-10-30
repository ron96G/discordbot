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

    def pretty_print(self):
        return f'"{self.artist} - {self.name}"{" (" + self.url + ")" if self.url != "" else ""}'

    def print(self):
        return f'TrackInfo: "{self.artist} - {self.name}" ({self.url})'


class SpotifyTrack(Track):
    def __init__(self, ctx: Context, info: List[TrackInfo], volume=0.5):
        super().__init__(ctx, info, volume)
