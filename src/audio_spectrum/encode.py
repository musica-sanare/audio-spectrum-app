"""Video encoding with ffmpeg: raw RGB frames in through a pipe, the source audio muxed in unchanged in time."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Literal

import numpy as np
import skia

from audio_spectrum.errors import EncodeError, FfmpegNotFoundError

Codec = Literal["h264", "prores"]


@dataclass(frozen=True)
class EncodeSettings:
    codec: Codec = "h264"
    crf: int = 14
    """H.264 quality: lower is better and larger. 14 keeps thin lines clean for chroma keying."""
    x264_preset: str = "medium"
    prores_profile: int = 2
    """ProRes profile: 2 = 422, 3 = 422 HQ, 4 = 4444 (full color resolution, sharpest edges for keying)."""
    include_audio: bool = True
    alpha: bool = False
    """Transparent background: frames carry straight alpha and the video keeps it. Needs ProRes 4444."""

    def __post_init__(self) -> None:
        if self.alpha and (self.codec != "prores" or self.prores_profile < 4):
            raise ValueError("a transparent background needs ProRes 4444 (codec 'prores', prores_profile 4)")


def ffmpeg_fps(fps: float) -> str:
    """Exact frame rate for ffmpeg, so 29.97 becomes 30000/1001 rather than a rounded decimal."""
    return str(Fraction(fps).limit_denominator(1001))


def build_command(
    output: Path, width: int, height: int, fps: float, settings: EncodeSettings, audio_path: Path | None,
    audio_range: tuple[float, float] | None = None,
) -> list[str]:
    """`audio_range` is (start, duration) in seconds of the audio to keep, for a video of part of a song."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg is not installed (brew install ffmpeg)")
    command = [
        ffmpeg, "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba" if settings.alpha else "rgb24", "-s", f"{width}x{height}",
        "-framerate", ffmpeg_fps(fps), "-i", "-",
    ]
    if settings.include_audio and audio_path is not None:
        # Chapters from WAV cue chunks would otherwise become an extra text track.
        command += ["-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0", "-map_chapters", "-1"]
        if audio_range is not None:
            start, duration = audio_range
            # atrim cuts at exact samples, and asetpts makes the kept audio start at time 0 like the frames.
            command += ["-af", f"atrim=start={start!r}:duration={duration!r},asetpts=PTS-STARTPTS"]
    # Tag BT.709 so editors show the key color as the pure color that was drawn.
    color = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    if settings.codec == "h264":
        command += [
            "-vf", "scale=out_color_matrix=bt709:out_range=tv",
            "-c:v", "libx264", "-preset", settings.x264_preset, "-crf", str(settings.crf),
            "-pix_fmt", "yuv420p", *color, "-movflags", "+faststart",
        ]
        audio_codec = ["-c:a", "aac", "-b:a", "320k"]
    else:
        command += [
            "-vf", "scale=out_color_matrix=bt709:out_range=tv",
            "-c:v", "prores_ks", "-profile:v", str(settings.prores_profile),
            "-pix_fmt", _prores_pixel_format(settings), *color,
        ]
        if settings.alpha:
            # Frames carry 8-bit alpha; 16-bit alpha would only make encoding slower and files larger.
            command += ["-alpha_bits", "8"]
        audio_codec = ["-c:a", "pcm_s24le"]
    if settings.include_audio and audio_path is not None:
        command += audio_codec
    return [*command, str(output)]


def _prores_pixel_format(settings: EncodeSettings) -> str:
    if settings.alpha:
        return "yuva444p10le"
    return "yuv444p10le" if settings.prores_profile >= 4 else "yuv422p10le"


def partial_path(output: Path) -> Path:
    """Temporary name in the output folder; it keeps the extension so ffmpeg picks the right container."""
    return output.with_name(f".{output.stem}.partial-{os.getpid()}{output.suffix}")


class VideoWriter:
    """Context manager that accepts frames as (height, width, 3) uint8 RGB arrays, or (height, width, 4) RGBA with
    straight alpha when the settings ask for alpha.

    The video is written to a temporary file next to the output and renamed only after ffmpeg succeeds, so a file
    with the final name is always complete. On any error or interruption the temporary file is removed.
    """

    def __init__(
        self, output: Path, width: int, height: int, fps: float,
        settings: EncodeSettings = EncodeSettings(), audio_path: Path | None = None,
        audio_range: tuple[float, float] | None = None,
    ):
        self._output = Path(output)
        self._partial = partial_path(self._output)
        self._command = build_command(self._partial, width, height, fps, settings, audio_path, audio_range)
        self._process: subprocess.Popen | None = None
        self._errors = None

    def __enter__(self) -> "VideoWriter":
        self._errors = tempfile.TemporaryFile()
        # A separate session keeps Ctrl+C away from ffmpeg; this writer decides when ffmpeg stops.
        self._process = subprocess.Popen(
            self._command, stdin=subprocess.PIPE, stderr=self._errors, start_new_session=True
        )
        return self

    def write(self, frame) -> None:
        try:
            self._process.stdin.write(frame.tobytes())
        except BrokenPipeError:
            self._process.wait()
            raise EncodeError(f"ffmpeg failed: {self._error_text()}") from None

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if exc_type is None:
                self._finish()
            else:
                self._abort()
        finally:
            self._errors.close()

    def _finish(self) -> None:
        try:
            self._process.stdin.close()
        except BrokenPipeError:
            pass
        self._process.wait()
        if self._process.returncode != 0:
            self._partial.unlink(missing_ok=True)
            raise EncodeError(f"ffmpeg failed: {self._error_text()}")
        self._partial.replace(self._output)

    def _abort(self) -> None:
        self._process.kill()
        try:
            self._process.stdin.close()
        except BrokenPipeError:
            pass
        self._process.wait()
        self._partial.unlink(missing_ok=True)

    def _error_text(self) -> str:
        self._errors.seek(0)
        lines = self._errors.read().decode(errors="replace").strip().splitlines()
        return lines[-1] if lines else f"exit code {self._process.returncode}"


def encode_png(frame: np.ndarray) -> bytes:
    """A (height, width, 3) uint8 RGB frame, or (height, width, 4) RGBA with straight alpha, as lossless PNG bytes."""
    if frame.shape[2] == 3:
        frame = np.dstack([frame, np.full(frame.shape[:2], 255, dtype=np.uint8)])
    image = skia.Image.fromarray(
        np.ascontiguousarray(frame), colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType
    )
    return bytes(image.encodeToData(skia.kPNG, 100))


def write_png(path: Path, frame: np.ndarray) -> None:
    """Write a frame as a lossless PNG (see `encode_png`), through a temporary file like videos."""
    path = Path(path)
    partial = partial_path(path)
    try:
        partial.write_bytes(encode_png(frame))
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
