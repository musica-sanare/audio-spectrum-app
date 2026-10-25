"""Audio file in, spectrum video out."""

import math
import os
import signal
import time
from collections import deque
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from audio_spectrum.analysis import analyze
from audio_spectrum.audio import load_audio
from audio_spectrum.encode import EncodeSettings, VideoWriter
from audio_spectrum.errors import Cancelled, OutputExistsError, TimeRangeError, WorkerError
from audio_spectrum.presets import Preset
from audio_spectrum.renderer import FrameRenderer

FRAMES_PER_TASK = 16

Progress = Callable[[int, int], None]
"""Called with (frames done, total frames): once with 0 when rendering starts, then after each frame."""
CancelCheck = Callable[[], bool]
"""Returns True to stop the render; checked before each frame."""


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
    values = analyze(audio, job.fps, job.preset.analysis)
    total = len(values)
    if progress is not None:
        progress(0, total)
    frames = _frames(job, values)
    # closing() stops the worker processes promptly when the render fails or is cancelled.
    with closing(frames), VideoWriter(output, job.width, job.height, job.fps, job.encode, job.audio_path) as writer:
        for index, frame in enumerate(frames, start=1):
            if cancel is not None and cancel():
                raise Cancelled(f"rendering {output.name} was cancelled")
            writer.write(frame)
            if progress is not None:
                progress(index, total)
    return RenderResult(output_path=output, frames=total, seconds=time.perf_counter() - started)


def render_stills(
    audio_path: Path, preset: Preset, times: list[float], width: int = 1920, height: int = 1080, fps: float = 30.0,
    transparent: bool = False,
) -> list[np.ndarray]:
    """Render the frames a video with these settings shows at the given times (seconds), as (height, width, 3) uint8
    RGB arrays, or (height, width, 4) RGBA with straight alpha when `transparent`. Each is byte-identical to that video
    frame before encoding. Raises TimeRangeError for a time outside the audio."""
    audio = load_audio(audio_path)
    values = analyze(audio, fps, preset.analysis)
    try:
        indices = [still_frame_index(seconds, fps, audio.duration) for seconds in times]
    except TimeRangeError as error:
        raise TimeRangeError(f"{Path(audio_path).name}: {error}") from None
    renderer = FrameRenderer(preset, width, height, transparent=transparent)
    return [renderer.render(values[min(index, len(values) - 1)]) for index in indices]


def still_frame_index(seconds: float, fps: float, duration: float) -> int:
    """The frame shown at `seconds`: frame n is on screen from n / fps until (n + 1) / fps."""
    if not 0 <= seconds < duration:
        raise TimeRangeError(f"{seconds:g} s is outside the audio (0 to {duration:.3f} s)")
    # The tolerance keeps times such as 2.3 s at 30 fps (68.99999... in floating point) on frame 69.
    return math.floor(seconds * fps + 1e-9)


def _frames(job: RenderJob, values: np.ndarray) -> Iterator[np.ndarray]:
    workers = job.workers or max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        renderer = FrameRenderer(job.preset, job.width, job.height, transparent=job.encode.alpha)
        for row in values:
            yield renderer.render(row)
        return
    chunks = [values[start:start + FRAMES_PER_TASK] for start in range(0, len(values), FRAMES_PER_TASK)]
    # Keep only a few chunks in flight so finished frames never pile up in memory faster than ffmpeg takes them.
    max_pending = workers * 2
    pool = ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker,
        initargs=(job.preset, job.width, job.height, job.encode.alpha),
    )
    try:
        pending = deque(pool.submit(_render_chunk, chunk) for chunk in chunks[:max_pending])
        for chunk in chunks[max_pending:]:
            yield from pending.popleft().result()
            pending.append(pool.submit(_render_chunk, chunk))
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


def _init_worker(preset: Preset, width: int, height: int, transparent: bool) -> None:
    global _worker_renderer
    # Ctrl+C reaches the whole process group; only the main process handles it.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _worker_renderer = FrameRenderer(preset, width, height, transparent=transparent)


def _render_chunk(rows: np.ndarray) -> list[np.ndarray]:
    return [_worker_renderer.render(row) for row in rows]
