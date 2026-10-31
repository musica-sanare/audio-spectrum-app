"""Audio file in, spectrum video out."""

import math
import os
import signal
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from audio_spectrum.analysis import AnalysisSettings, analyze
from audio_spectrum.audio import load_audio
from audio_spectrum.encode import EncodeSettings, VideoWriter
from audio_spectrum.errors import BackdropError, Cancelled, OutputExistsError, TimeRangeError, WorkerError
from audio_spectrum.presets import Preset
from audio_spectrum.renderer import FrameRenderer

FRAMES_PER_TASK = 16

Progress = Callable[[int, int], None]
"""Called with (frames done, total frames): once with 0 when rendering starts, then after each frame."""
CancelCheck = Callable[[], bool]
"""Returns True to stop the render; checked before each frame."""


class Backdrop(Protocol):
    """The picture under the spectrum, frame by frame, supplied by an app that embeds this one (for example a background
    image with lyrics captions). It is sent to every render worker process, so it must be picklable: keep paths and
    settings in it and load pictures lazily."""

    def frame(self, index: int, seconds: float, width: int, height: int) -> np.ndarray:
        """The (height, width, 3) uint8 RGB picture under the spectrum at frame `index` of the whole song, which the
        video shows at `seconds` (= index / fps), also when only part of the song is rendered."""
        ...


@dataclass(frozen=True)
class RenderJob:
    audio_path: Path
    output_path: Path
    preset: Preset
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    encode: EncodeSettings = EncodeSettings()
    workers: int = 0
    """Render processes; 0 picks one per CPU core minus one, 1 renders in this process."""
    overwrite: bool = False
    start: float = 0.0
    """Render only part of the song, from this time in seconds. The clip begins with the frame the full video shows at
    that time, so its frames are identical to the full video's."""
    duration: float | None = None
    """Length of that part in seconds; None means to the end of the song."""
    backdrop: Backdrop | None = None
    """Pictures to draw the spectrum on instead of the preset's background color; see `Backdrop`."""

    def __post_init__(self) -> None:
        if not self.start >= 0:
            raise ValueError(f"start must be 0 or more, got {self.start}")
        if self.duration is not None and not self.duration > 0:
            raise ValueError(f"duration must be above 0, got {self.duration}")
        if self.backdrop is not None and self.encode.alpha:
            raise ValueError("a backdrop cannot be combined with a transparent background")


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    frames: int
    seconds: float


def render_video(job: RenderJob, progress: Progress | None = None, cancel: CancelCheck | None = None) -> RenderResult:
    """Render the whole video. Raises an AudioSpectrumError subclass on failure and Cancelled when `cancel` says so;
    in both cases no output file is left behind.

    With more than one worker, frames are drawn in separate processes that re-import the caller's main script, so a
    script calling this must do so under `if __name__ == "__main__":`.
    """
    started = time.perf_counter()
    output = Path(job.output_path)
    if output.exists() and not job.overwrite:
        raise OutputExistsError(f"{output} already exists (use overwrite to replace it)")
    audio = load_audio(job.audio_path)
    # The whole song is analyzed even for a part, so smoothing starts from the same state as in the full video.
    values = analyze(audio, job.fps, job.preset.analysis)
    first, last = _frame_range(job, audio.duration, len(values))
    whole_song = (first, last) == (0, len(values))
    values = values[first:last]
    audio_range = None if whole_song else (first / job.fps, len(values) / job.fps)
    total = len(values)
    if progress is not None:
        progress(0, total)
    frames = _frames(job, values, first)
    writer = VideoWriter(output, job.width, job.height, job.fps, job.encode, job.audio_path, audio_range)
    # closing() stops the worker processes promptly when the render fails or is cancelled.
    with closing(frames), writer:
        for index, frame in enumerate(frames, start=1):
            if cancel is not None and cancel():
                raise Cancelled(f"rendering {output.name} was cancelled")
            writer.write(frame)
            if progress is not None:
                progress(index, total)
    return RenderResult(output_path=output, frames=total, seconds=time.perf_counter() - started)


def render_stills(
    audio_path: Path, preset: Preset, times: list[float], width: int = 1920, height: int = 1080, fps: float = 30.0,
    transparent: bool = False, backdrop: Backdrop | None = None,
) -> list[np.ndarray]:
    """Render the frames a video with these settings shows at the given times (seconds), as (height, width, 3) uint8
    RGB arrays, or (height, width, 4) RGBA with straight alpha when `transparent`. Each is byte-identical to that video
    frame before encoding. Raises TimeRangeError for a time outside the audio."""
    return Preview(audio_path, fps).frames(preset, times, width, height, transparent, backdrop)


class Preview:
    """Frames of one song for quick looks, as in a GUI. The song is decoded once and the analysis is kept for the
    last few analysis settings, so a change of the look alone renders a 1080p frame in tens of milliseconds. Frames are
    byte-identical to the video's. Not thread-safe: use one per thread, or a lock."""

    KEPT_ANALYSES = 4

    def __init__(self, audio_path: Path, fps: float = 30.0):
        self.audio_path = Path(audio_path)
        self.fps = fps
        self._audio = load_audio(self.audio_path)
        self._analyses: OrderedDict[AnalysisSettings, np.ndarray] = OrderedDict()
        self._renderer: FrameRenderer | None = None

    @property
    def duration(self) -> float:
        """Length of the song in seconds."""
        return self._audio.duration

    def frames(
        self, preset: Preset, times: list[float], width: int = 1920, height: int = 1080, transparent: bool = False,
        backdrop: Backdrop | None = None,
    ) -> list[np.ndarray]:
        """The frames a video with these settings shows at the given times (seconds), as `render_stills` returns
        them. Raises TimeRangeError for a time outside the song."""
        try:
            indices = [still_frame_index(seconds, self.fps, self.duration) for seconds in times]
        except TimeRangeError as error:
            raise TimeRangeError(f"{self.audio_path.name}: {error}") from None
        values = self._values(preset.analysis)
        renderer = self._renderer_for(preset, width, height, transparent)
        indices = [min(index, len(values) - 1) for index in indices]
        return [_draw(renderer, values[index], index, backdrop, self.fps) for index in indices]

    def _values(self, settings: AnalysisSettings) -> np.ndarray:
        if settings in self._analyses:
            self._analyses.move_to_end(settings)
        else:
            self._analyses[settings] = analyze(self._audio, self.fps, settings)
            while len(self._analyses) > self.KEPT_ANALYSES:
                self._analyses.popitem(last=False)
        return self._analyses[settings]

    def _renderer_for(self, preset: Preset, width: int, height: int, transparent: bool) -> FrameRenderer:
        current = self._renderer
        if current is None or (current.preset, current.width, current.height, current.transparent) != (
            preset, width, height, transparent
        ):
            self._renderer = FrameRenderer(preset, width, height, transparent=transparent)
        return self._renderer


def _frame_range(job: RenderJob, audio_duration: float, total: int) -> tuple[int, int]:
    """First and last (exclusive) frame of the full video that the job renders."""
    if job.start == 0 and job.duration is None:
        return 0, total
    try:
        first = min(still_frame_index(job.start, job.fps, audio_duration), total - 1)
    except TimeRangeError as error:
        raise TimeRangeError(f"{Path(job.audio_path).name}: start {error}") from None
    if job.duration is None:
        return first, total
    count = max(1, math.ceil(job.duration * job.fps - 1e-9))
    return first, min(total, first + count)


def still_frame_index(seconds: float, fps: float, duration: float) -> int:
    """The frame shown at `seconds`: frame n is on screen from n / fps until (n + 1) / fps."""
    if not 0 <= seconds < duration:
        raise TimeRangeError(f"{seconds:g} s is outside the audio (0 to {duration:.3f} s)")
    # The tolerance keeps times such as 2.3 s at 30 fps (68.99999... in floating point) on frame 69.
    return math.floor(seconds * fps + 1e-9)


def _frames(job: RenderJob, values: np.ndarray, first: int = 0) -> Iterator[np.ndarray]:
    """The frames for `values`, whose first row is frame `first` of the whole song."""
    workers = job.workers or max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        renderer = FrameRenderer(job.preset, job.width, job.height, transparent=job.encode.alpha)
        for offset, row in enumerate(values):
            yield _draw(renderer, row, first + offset, job.backdrop, job.fps)
        return
    chunks = [
        (first + start, values[start:start + FRAMES_PER_TASK]) for start in range(0, len(values), FRAMES_PER_TASK)
    ]
    # Keep only a few chunks in flight so finished frames never pile up in memory faster than ffmpeg takes them.
    max_pending = workers * 2
    pool = ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker,
        initargs=(job.preset, job.width, job.height, job.encode.alpha, job.backdrop, job.fps),
    )
    try:
        pending = deque(pool.submit(_render_chunk, *chunk) for chunk in chunks[:max_pending])
        for chunk in chunks[max_pending:]:
            yield from pending.popleft().result()
            pending.append(pool.submit(_render_chunk, *chunk))
        while pending:
            yield from pending.popleft().result()
    except BrokenProcessPool:
        raise WorkerError(
            "a render worker process died; when calling the API from a script, run it under "
            "`if __name__ == \"__main__\":` (worker processes re-import the main script), or use workers=1"
        ) from None
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


_worker_renderer: FrameRenderer | None = None
_worker_backdrop: Backdrop | None = None
_worker_fps = 30.0


def _init_worker(
    preset: Preset, width: int, height: int, transparent: bool, backdrop: Backdrop | None, fps: float
) -> None:
    global _worker_renderer, _worker_backdrop, _worker_fps
    # Ctrl+C reaches the whole process group; only the main process handles it.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _worker_renderer = FrameRenderer(preset, width, height, transparent=transparent)
    _worker_backdrop, _worker_fps = backdrop, fps


def _render_chunk(first: int, rows: np.ndarray) -> list[np.ndarray]:
    return [
        _draw(_worker_renderer, row, first + offset, _worker_backdrop, _worker_fps) for offset, row in enumerate(rows)
    ]


def _draw(renderer: FrameRenderer, row: np.ndarray, index: int, backdrop: Backdrop | None, fps: float) -> np.ndarray:
    if backdrop is None:
        return renderer.render(row)
    return renderer.render(row, under=_backdrop_picture(backdrop, index, fps, renderer.width, renderer.height))


def _backdrop_picture(backdrop: Backdrop, index: int, fps: float, width: int, height: int) -> np.ndarray:
    try:
        picture = np.asarray(backdrop.frame(index, index / fps, width, height))
    except Exception as error:
        # Raised in a worker process, the error travels to the caller, so it carries its cause as text.
        raise BackdropError(f"the backdrop failed at frame {index}: {type(error).__name__}: {error}") from None
    if picture.shape != (height, width, 3) or picture.dtype != np.uint8:
        raise BackdropError(
            f"the backdrop returned a {picture.dtype} picture of shape {picture.shape} at frame {index}; "
            f"expected uint8 of shape ({height}, {width}, 3)"
        )
    return picture
