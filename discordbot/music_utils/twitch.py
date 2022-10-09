import logging
import re
from shutil import which
from typing import Any, Dict, Union

import streamlink
from twitchAPI.twitch import Twitch as TwitchAPI

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
TWITCH_USER_REGEX = re.compile(r"^https:\/\/www.twitch.tv\/(\S+)$")


class TwitchError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


class Twitch:
    log = logging.getLogger("svc")

    def __init__(self, service: Union[TwitchAPI, None]):
        self.log.info("Init Twitch Service")
        self.service = service

    def __del__(self):
        pass

    def is_twitch_url(self, url: str) -> bool:
        return "twitch" in url

    def is_ffmpeg_installed(self) -> bool:
        return which("ffmpeg") is not None

    def url_to_username(self, url: str) -> str:
        found_id = TWITCH_USER_REGEX.search(url)
        if found_id:
            return found_id.group(1)
        return ""

    def _get_direct_stream_link(self, twitch_url: str, quality="480p") -> str:
        self.log.debug(f"Trying to find stream url for twitch url '{twitch_url}'")

        try:
            stream_qls: Dict[str, Any] = streamlink.streams(twitch_url)

        except streamlink.NoPluginError:
            raise ValueError(f"No stream available for {twitch_url}")

        if quality not in stream_qls:
            self.log.warn(f"Missing quality {quality} in {stream_qls.keys()}")
            raise ValueError(f"No stream available for given quality {quality}")

        return stream_qls[quality].url

    def extract_info(self, twitch_url: str) -> Dict[str, str]:
        username = self.url_to_username(twitch_url)
        self.log.debug(f"Searching for information about twitch user {username}")

        if self.service is not None:
            # https://pytwitchapi.readthedocs.io/en/latest/modules/twitchAPI.twitch.html#twitchAPI.twitch.Twitch.get_users
            users = self.service.get_users(logins=[username])
            user = users["data"][0]

            if user is not None:
                return {
                    "url": twitch_url,
                    "title": f"{user['display_name']} - Twitch",
                    "thumbnail": user["profile_image_url"],
                }

        # fallback if no service or no user has been returned
        return {
            "url": twitch_url,
            "title": "Internal Server: Missing info embedding",
            "thumbnail": f"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ3Acdw0IWPRMwkDOFu78_Lf-ltHq2TsFhV8A&usqp=CAU",
        }
