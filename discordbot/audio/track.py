from dataclasses import dataclass, field
from typing import Callable, List, Optional

from common.context import Context
from discord import FFmpegPCMAudio, PCMVolumeTransformer

STREAM_FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

FFMPEG_OPTS = {
    "before_options": "",
    "options": "-vn",
}


@dataclass
class TrackInfo:
    url: str
    title: str
    thumbnail: Optional[str] = ""
    download_url: Optional[str] = ""
    stream = True

    def print(self):
        return f'TrackInfo: "{self.title}" ({self.url})'

    def pretty_print(self):
        return f'"{self.title}" ({self.url if self.url is not None else "-"})'


class Track:
    priority: int
    context: Context
    info: List[TrackInfo]
    _player: PCMVolumeTransformer
    current = 0
    length = 0
    volume: float
    error: Exception = None

    before_build: Callable[[TrackInfo], None] = None
    after_build: Callable[[TrackInfo, PCMVolumeTransformer], None] = None

    def __init__(
        self, ctx: Context, info: List[TrackInfo], volume=0.5, error: Exception = None
    ):
        if isinstance(info, list):
            self.info = info
        else:
            self.info = [info]

        self.context = ctx
        self.length = len(self.info)
        self.current = 0
        self._player = None
        self.volume = volume
        self.error = error

    def __len__(self):
        return self.length - self.current

    def __del__(self):
        print(f"Deleting track {self.info}")

    def _build_player(self, download_url: str, stream=True):
        return PCMVolumeTransformer(
            FFmpegPCMAudio(
                download_url, **STREAM_FFMPEG_OPTS if stream else FFMPEG_OPTS
            ),
            self.volume,
        )

    def as_prio_item(self):
        return PrioritizedItem(self.priority, self)

    def is_failed(self):
        return self.error is not None

    def max_len(self):
        return self.length

    def get_remaining_tracks(self) -> List[TrackInfo]:
        return self.info[self.current :]

    def pretty_print(self) -> str:
        return f"Track: {len(self)} songs left"

    def set_before_build(self, func: Callable[[TrackInfo], None]):
        self.before_build = func

    def set_after_build(self, func: Callable[[TrackInfo, PCMVolumeTransformer], None]):
        self.after_build = func

    # get the info about the currently active track
    def get_current_info(self) -> TrackInfo:
        if self.current == 0:
            raise ValueError("There is no active track. Select the next first.")
        return self.info[self.current - 1]

    def hasNext(self):
        return self.current < self.length

    async def next(self):
        if not self.hasNext():
            return None

        track_info = self.info[self.current]

        if self.before_build is not None:
            try:
                await self.before_build(track_info)
            except Exception as e:
                self.error = e
                return

        self._player = self._build_player(track_info.download_url, track_info.stream)

        if self.after_build is not None:
            try:
                await self.after_build(track_info, self._player)
            except Exception as e:
                self.error = e
                return

        self.current += 1
        return self._player


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: Track = field(compare=False)
