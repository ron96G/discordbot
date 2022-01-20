import logging
import re
from typing import Any, Dict, List

import spotipy

SPOTIFY_MARKET = "DE"
SPOTIFY_TRACK_ID_REGEX = re.compile(r".*spotify\.com\/track\/(.*?)\?si=.*")
SPOTIFY_ALBUM_ID_REGEX = re.compile(r".*spotify\.com\/album\/(.*?)\?si=.*")
SPOTIFY_PLAYLIST_ID_REGEX = re.compile(r".*spotify\.com\/playlist\/(.*?)\?si=.*")
MAX_ENTRIES = 10


class SpotifyError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


# See https://developer.spotify.com/documentation/web-api/reference/#/
class Spotify:
    def __init__(self, service: spotipy.Spotify):
        self.service = service
        self.log = logging.getLogger("svc")

    def is_spotify_url(self, url: str) -> bool:
        return (
            self.is_spotify_album(url)
            or self.is_spotify_track(url)
            or self.is_spotify_playlist(url)
        )

    def is_spotify_album(self, url: str) -> bool:
        return bool(SPOTIFY_ALBUM_ID_REGEX.match(url))

    def is_spotify_track(self, url: str) -> bool:
        return bool(SPOTIFY_TRACK_ID_REGEX.match(url))

    def is_spotify_playlist(self, url: str) -> bool:
        return bool(SPOTIFY_PLAYLIST_ID_REGEX.match(url))

    async def get_info(self, url: str) -> List[Dict[str, str]]:
        tracks = []
        if self.is_spotify_track(url):
            tracks.append(await self.get_track_info(url))

        elif self.is_spotify_album(url):
            tracks = await self.get_album_tracks_info(url)

        elif self.is_spotify_playlist(url):
            tracks = await self.get_playlist_tracks_info(url)

        else:
            raise SpotifyError("Invalid spotify url")

        return tracks

    async def get_track_info(self, id_or_url: str) -> Dict[str, str]:
        self.log.info(f'Searching spotify for track "{id_or_url}"')
        try:
            track = self.service.track(id_or_url, market=SPOTIFY_MARKET)

        except Exception as e:
            raise SpotifyError(f"failed to get track {id_or_url}", e)

        self.log.info(f'Found track "{track["name"]}"')

        return {
            "artist": track["artists"][0]["name"],
            "name": track["name"],
            "thumbnail": track["album"]["images"][0]["url"],
        }

    async def get_playlist_tracks_info(self, id_or_url: str) -> List[Dict[str, str]]:
        self.log.info(f'Searching spotify for playlist "{id_or_url}"')

        try:
            playlist = self.service.playlist(
                id_or_url,
                market=SPOTIFY_MARKET,
                fields="tracks.items(track(name, artists.name, album(images(url))))",
            )

        except Exception as e:
            raise SpotifyError(f"failed to get playlist {id_or_url}", e)

        playlist_tracks = [t["track"] for t in playlist["tracks"]["items"]]
        tracks = []
        if len(playlist_tracks) > MAX_ENTRIES:
            self.log.warn(
                f"Playlist has more than {MAX_ENTRIES} tracks, only the first {MAX_ENTRIES} will be played"
            )
            playlist_tracks = playlist_tracks[: MAX_ENTRIES - 1]

        for track in playlist_tracks:
            tracks.append(
                {
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "thumbnail": track["album"]["images"][0]["url"],
                }
            )

        return tracks

    async def get_album_tracks_info(self, id_or_url: str) -> List[Dict[str, str]]:
        self.log.info(f'Searching spotify for album "{id_or_url}"')
        try:
            album = self.service.album(id_or_url)

        except Exception as e:
            raise SpotifyError(f"failed to get album {id_or_url}", e)

        self.log.info(
            f'Found album "{album["name"]}" with {len(album["tracks"]["items"])} tracks'
        )

        album_tacks = album["tracks"]["items"]
        tracks = []
        album_thumbnail = album["images"][0]["url"]

        if len(album_tacks) > MAX_ENTRIES:
            self.log.warn(
                f"Album has more than {MAX_ENTRIES} tracks, only the first {MAX_ENTRIES} will be played"
            )
            album_tacks = album_tacks[: MAX_ENTRIES - 1]

        for track in album_tacks:
            tracks.append(
                {
                    "artist": track["artists"][0]["name"],
                    "name": track["name"],
                    "thumbnail": album_thumbnail,
                }
            )

        return tracks
