import logging
from typing import Dict

import streamlink
from streamlink.stream import Stream


class LinksError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


class LinksService:

    log = logging.getLogger()

    def __init__(self):
        pass

    def is_url(self, url: str) -> bool:
        return "https://" in url

    def find_stream(self, url: str, quality="480p") -> str:
        try:
            streams: Dict[str, Stream] = streamlink.streams(url)

            if quality not in streams:
                self.log.warn(f"Missing quality {quality} in {streams.keys()}")
                raise LinksError(f"Defined quality {quality} is not in result set")

            return streams[quality].url

        except streamlink.NoPluginError:
            raise ValueError(f"No stream available for {url}")
