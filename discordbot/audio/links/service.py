import logging
from typing import Dict, List

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

    def _get_quality(self, given: List[str], desired: List[str]):
        for item in desired:
            if item in given:
                return item

    def find_stream(self, url: str, quality="480p") -> str:
        try:
            streams: Dict[str, Stream] = streamlink.streams(url)

            quality = self._get_quality(
                streams.keys(), ["best", "good", "480p", "720p"]
            )

            if quality is None:
                self.log.warn(f"Missing quality {quality} in {streams.keys()}")
                raise LinksError(f"Defined quality {quality} is not in result set")

            return streams[quality].url

        except streamlink.NoPluginError:
            raise ValueError(f"No stream available for {url}")
