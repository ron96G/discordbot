import logging
import re
from typing import Any, Dict, List

import spotipy

SPOTIFY_MARKET = "DE"
SPOTIFY_TRACK_ID_REGEX = re.compile(r".*spotify\.com\/track\/(.*?)\?si=.*")
SPOTIFY_ALBUM_ID_REGEX = re.compile(r".*spotify\.com\/album\/(.*?)\?si=.*")
SPOTIFY_PLAYLIST_ID_REGEX = re.compile(r".*spotify\.com\/playlist\/(.*?)\?si=.*")

class SpotifyError(Exception):
    def __init__(self, msg, thrown = None):
        super().__init__(msg)
        self.thrown = thrown

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
            raise NotImplementedError("Playlists are not supported yet")

        else:
            raise SpotifyError("Invalid spotify url")

        return tracks
            

    async def get_track_info(self, id_or_url: str) -> Dict[str, str]:
        self.log.info(f'Searching spotify for track "{id_or_url}"')
        try:
            track = self.service.track(id_or_url, market=SPOTIFY_MARKET)

        except Exception as e:
            raise SpotifyError(f'failed to get track {id_or_url}', e)

        self.log.info(f'Found track "{track["name"]}"')

        return {
            "artist": track["artists"][0]["name"],
            "name": track["name"],
            "thumbnail": track["album"]["images"][0]["url"],
        }

    async def get_playlist_tracks_info(self, id_or_url: str) -> List[Dict[str, str]]:
        self.log.info(f'Searching spotify for playlist "{id_or_url}"')

        # reduce scope of response payload --> items(track(name,href,album(name,href)))
        _ = self.service.playlist(id_or_url)
        raise NotImplementedError("Playlists are not supported yet")

    async def get_album_tracks_info(self, id_or_url: str) -> List[Dict[str, str]]:
        self.log.info(f'Searching spotify for album "{id_or_url}"')
        try:
            album = self.service.album(id_or_url)

        except Exception as e:
            raise SpotifyError(f'failed to get album {id_or_url}', e)

        self.log.info(
            f'Found album "{album["name"]}" with {len(album["tracks"]["items"])} tracks'
        )

        album_tacks = album["tracks"]["items"]
        tracks = []
        album_thumbnail = album["images"][0]["url"]

        if len(album_tacks) > 10:
            self.log.warn(
                "Album has more than 10 tracks, only the first 10 will be played"
            )
            album_tacks = album_tacks[:9]

        for track in album_tacks:
            tracks.append(
                {
                    "artist": track["artists"][0]["name"],
                    "name": track["name"],
                    "thumbnail": album_thumbnail,
                }
            )

        return tracks
