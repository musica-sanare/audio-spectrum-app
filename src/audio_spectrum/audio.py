"""Audio decoding into float sample arrays."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import soundfile as sf

from audio_spectrum.errors import DecodeError, FfmpegNotFoundError

ChannelMode = Literal["mix", "left", "right"]

DEFAULT_FFMPEG_SAMPLE_RATE = 48000


@dataclass(frozen=True)
class Audio:
    """Decoded audio. `samples` has shape (frames, channels), float32 in [-1, 1]."""

    samples: np.ndarray
    sample_rate: int

    @property
    def num_samples(self) -> int:
        return self.samples.shape[0]

    @property
    def duration(self) -> float:
        return self.num_samples / self.sample_rate

    def channel(self, mode: ChannelMode) -> np.ndarray:
        """Return one mono signal: the mean of all channels, or the left or right channel."""
        if mode == "mix":
            return self.samples.mean(axis=1, dtype=np.float32)
        index = 0 if mode == "left" else 1
        return self.samples[:, min(index, self.samples.shape[1] - 1)]


def load_audio(path: str | Path) -> Audio:
    """Decode an audio file. Formats libsndfile cannot read are decoded with ffmpeg."""
    path = Path(path)
    if not path.is_file():
        raise DecodeError(f"{path}: file not found")
    try:
        samples, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    except sf.LibsndfileError:
        return _load_with_ffmpeg(path)
    if len(samples) == 0:
        raise DecodeError(f"{path}: no audio samples")
    return Audio(samples=samples, sample_rate=sample_rate)


def _load_with_ffmpeg(path: Path) -> Audio:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError(f"cannot decode {path.name}: ffmpeg is not installed (brew install ffmpeg)")
    channels = 2
    result = subprocess.run(
        [
            ffmpeg, "-v", "error", "-i", str(path),
            "-f", "f32le", "-acodec", "pcm_f32le",
            "-ac", str(channels), "-ar", str(DEFAULT_FFMPEG_SAMPLE_RATE), "-",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip().splitlines()
        raise DecodeError(f"{path}: cannot decode audio ({detail[-1] if detail else 'unknown error'})")
    samples = np.frombuffer(result.stdout, dtype="<f4").reshape(-1, channels)
    if len(samples) == 0:
        raise DecodeError(f"{path}: no audio samples")
    return Audio(samples=samples, sample_rate=DEFAULT_FFMPEG_SAMPLE_RATE)
