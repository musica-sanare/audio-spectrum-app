"""Per-frame spectrum analysis.

Frame `n` of the video shows the audio at time `n / fps`. The analysis window is centered on that time, so what is
seen matches what is heard. Values are normalized to [0, 1] per band.
"""

import math
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from audio_spectrum.audio import Audio, ChannelMode

FrequencyScale = Literal["log", "linear"]
MagnitudeScale = Literal["db", "linear"]

FRAMES_PER_CHUNK = 512
TILT_REFERENCE_FREQUENCY = 1000.0


class AnalysisSettings(BaseModel):
    """How audio becomes band values. Defaults are the `default` preset's values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fft_size: int = Field(4096, ge=256, le=32768)
    """FFT length in samples, a power of two. Longer resolves low notes better but reacts more slowly."""
    bands: int = Field(512, ge=1, le=8192)
    frequency_scale: FrequencyScale = "log"
    min_frequency: float = Field(30.0, ge=0.0)
    max_frequency: float = Field(16000.0, gt=0.0)
    """Upper edge in Hz; limited to the audio's Nyquist frequency (`inf` means up to Nyquist)."""
    magnitude_scale: MagnitudeScale = "db"
    db_floor: float = Field(-48.0, lt=0.0)
    """Level shown as zero height on the dB scale; full scale is 0 dB."""
    gain: float = Field(1.0, gt=0.0)
    tilt_db_per_octave: float = Field(3.0, ge=-24.0, le=24.0)
    """Boost per octave above 1 kHz (and cut below it). Music loses energy toward high frequencies, so a positive tilt
    makes the bands look more even."""
    channel: ChannelMode = "mix"
    attack_seconds: float = Field(0.01, ge=0.0)
    release_seconds: float = Field(0.15, ge=0.0)

    @model_validator(mode="after")
    def _check(self) -> "AnalysisSettings":
        if self.fft_size & (self.fft_size - 1):
            raise ValueError(f"fft_size must be a power of two, got {self.fft_size}")
        if self.max_frequency <= self.min_frequency:
            raise ValueError("max_frequency must be greater than min_frequency")
        if self.frequency_scale == "log" and self.min_frequency <= 0:
            raise ValueError("min_frequency must be above 0 on a log frequency scale")
        return self


def frame_count(num_samples: int, sample_rate: int, fps: float) -> int:
    """Number of video frames needed to cover the audio: frame times 0, 1/fps, ... up to the last sample."""
    return max(1, math.ceil(num_samples * fps / sample_rate))


def analyze(audio: Audio, fps: float, settings: AnalysisSettings = AnalysisSettings()) -> np.ndarray:
    """Return band values with shape (frames, bands), float32 in [0, 1]."""
    signal = audio.channel(settings.channel)
    num_frames = frame_count(audio.num_samples, audio.sample_rate, fps)
    nyquist = audio.sample_rate / 2
    max_frequency = min(settings.max_frequency, nyquist)
    bands = _BandMap(settings, audio.sample_rate, max_frequency)

    window = np.blackman(settings.fft_size).astype(np.float32)
    # Scale so that a full-scale sine reads 1.0 in its bin.
    amplitude_scale = 2.0 / window.sum() * settings.gain
    bin_gains = amplitude_scale * _tilt_gains(settings, audio.sample_rate)
    half = settings.fft_size // 2
    padded = np.pad(signal, (half, half + settings.fft_size))
    centers = np.round(np.arange(num_frames) * audio.sample_rate / fps).astype(np.int64)
    offsets = np.arange(settings.fft_size)

    values = np.empty((num_frames, settings.bands), dtype=np.float32)
    for start in range(0, num_frames, FRAMES_PER_CHUNK):
        chunk_centers = centers[start:start + FRAMES_PER_CHUNK]
        windows = padded[chunk_centers[:, None] + offsets[None, :]] * window
        magnitudes = np.abs(np.fft.rfft(windows, axis=1)) * bin_gains
        values[start:start + len(chunk_centers)] = _normalize(bands.apply(magnitudes), settings)

    return _smooth(values, fps, settings.attack_seconds, settings.release_seconds)


def _tilt_gains(settings: AnalysisSettings, sample_rate: int) -> np.ndarray:
    frequencies = np.fft.rfftfreq(settings.fft_size, d=1.0 / sample_rate)
    if settings.tilt_db_per_octave == 0:
        return np.ones_like(frequencies, dtype=np.float32)
    lowest = sample_rate / settings.fft_size
    octaves = np.log2(np.maximum(frequencies, lowest) / TILT_REFERENCE_FREQUENCY)
    return (10.0 ** (settings.tilt_db_per_octave * octaves / 20.0)).astype(np.float32)


class _BandMap:
    """Maps FFT bins to bands: the maximum of the bins inside each band, or an interpolated value for bands narrower
    than one bin."""

    def __init__(self, settings: AnalysisSettings, sample_rate: int, max_frequency: float):
        bin_width = sample_rate / settings.fft_size
        if settings.frequency_scale == "log":
            edges = np.geomspace(settings.min_frequency, max_frequency, settings.bands + 1)
            centers = np.sqrt(edges[:-1] * edges[1:])
        else:
            edges = np.linspace(settings.min_frequency, max_frequency, settings.bands + 1)
            centers = (edges[:-1] + edges[1:]) / 2
        self._low = np.ceil(edges[:-1] / bin_width).astype(np.int64)
        self._high = np.ceil(edges[1:] / bin_width).astype(np.int64)
        self._has_bins = self._high > self._low
        self._center_bins = centers / bin_width

    def apply(self, magnitudes: np.ndarray) -> np.ndarray:
        num_bins = magnitudes.shape[1]
        result = np.empty((magnitudes.shape[0], len(self._low)), dtype=np.float32)
        narrow = np.flatnonzero(~self._has_bins)
        positions = np.clip(self._center_bins[narrow], 0, num_bins - 1)
        below = np.floor(positions).astype(np.int64)
        above = np.minimum(below + 1, num_bins - 1)
        fraction = (positions - below).astype(np.float32)
        result[:, narrow] = magnitudes[:, below] * (1 - fraction) + magnitudes[:, above] * fraction
        for band in np.flatnonzero(self._has_bins):
            result[:, band] = magnitudes[:, self._low[band]:min(self._high[band], num_bins)].max(axis=1)
        return result


def _normalize(magnitudes: np.ndarray, settings: AnalysisSettings) -> np.ndarray:
    if settings.magnitude_scale == "linear":
        return np.clip(magnitudes, 0.0, 1.0)
    floor = settings.db_floor
    decibels = 20.0 * np.log10(np.maximum(magnitudes, 10.0 ** (floor / 20.0)))
    return np.clip((decibels - floor) / -floor, 0.0, 1.0)


def _smooth(values: np.ndarray, fps: float, attack_seconds: float, release_seconds: float) -> np.ndarray:
    """One-pole smoothing with separate rise (attack) and fall (release) speeds. Zero disables that direction."""
    attack = _smoothing_coefficient(attack_seconds, fps)
    release = _smoothing_coefficient(release_seconds, fps)
    if attack == 1.0 and release == 1.0:
        return values
    smoothed = np.empty_like(values)
    state = np.zeros(values.shape[1], dtype=np.float32)
    for index, target in enumerate(values):
        coefficient = np.where(target > state, attack, release)
        state = state + (target - state) * coefficient
        smoothed[index] = state
    return smoothed


def _smoothing_coefficient(seconds: float, fps: float) -> float:
    if seconds <= 0:
        return 1.0
    return float(1.0 - math.exp(-1.0 / (fps * seconds)))
