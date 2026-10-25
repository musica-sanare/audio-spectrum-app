"""Audio file in, spectrum video out."""

import os
from collections import deque
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from audio_spectrum.analysis import analyze
from audio_spectrum.audio import load_audio
from audio_spectrum.encode import EncodeSettings, VideoWriter
from audio_spectrum.presets import Preset
from audio_spectrum.renderer import FrameRenderer

FRAMES_PER_TASK = 16

Progress = Callable[[int, int], None]


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


def render_video(job: RenderJob, progress: Progress | None = None) -> int:
    """Render the whole video and return the number of frames written."""
    audio = load_audio(job.audio_path)
    values = analyze(audio, job.fps, job.preset.analysis)
    total = len(values)
    with VideoWriter(job.output_path, job.width, job.height, job.fps, job.encode, job.audio_path) as writer:
        for index, frame in enumerate(_frames(job, values), start=1):
            writer.write(frame)
            if progress is not None:
                progress(index, total)
    return total


def _frames(job: RenderJob, values: np.ndarray) -> Iterator[np.ndarray]:
    workers = job.workers or max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        renderer = FrameRenderer(job.preset, job.width, job.height)
        for row in values:
            yield renderer.render(row)
        return
    chunks = [values[start:start + FRAMES_PER_TASK] for start in range(0, len(values), FRAMES_PER_TASK)]
    # Keep only a few chunks in flight so finished frames never pile up in memory faster than ffmpeg takes them.
    max_pending = workers * 2
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker, initargs=(job.preset, job.width, job.height)
    ) as pool:
        pending = deque(pool.submit(_render_chunk, chunk) for chunk in chunks[:max_pending])
        for chunk in chunks[max_pending:]:
            yield from pending.popleft().result()
            pending.append(pool.submit(_render_chunk, chunk))
        while pending:
            yield from pending.popleft().result()


_worker_renderer: FrameRenderer | None = None


def _init_worker(preset: Preset, width: int, height: int) -> None:
    global _worker_renderer
    _worker_renderer = FrameRenderer(preset, width, height)


def _render_chunk(rows: np.ndarray) -> list[np.ndarray]:
    return [_worker_renderer.render(row) for row in rows]
