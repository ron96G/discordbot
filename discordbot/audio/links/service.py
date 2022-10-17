import logging
from typing import Dict, List

import streamlink
from streamlink.stream import Stream


class LinksError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


def first_desired_in_list(given: List[str], desired: List[str]):
    if given is None or desired is None:
        return None
    for item in desired:
        if item in given:
            return item


class LinksService:

    log = logging.getLogger()

    def __init__(self):
        pass

    def is_url(self, url: str) -> bool:
        return "https://" in url

    def find_stream(
        self, url: str, qualities: List[str] = ["best", "good", "720p", "480p"]
    ) -> str:
        try:
            streams: Dict[str, Stream] = streamlink.streams(url)
            if streams is not None:
                available_qualities = streams.keys()

            if available_qualities is None or len(available_qualities) == 0:
                raise LinksError(f"No stream found for {url}")

            quality = first_desired_in_list(available_qualities, qualities)

            if quality is None:
                self.log.warn(
                    f"Missing any value of {qualities} in {available_qualities}"
                )
                quality = available_qualities[0]  # select any quality

            return streams[quality].url

        except streamlink.NoPluginError:
            raise LinksError("Provided URL is not supported")
