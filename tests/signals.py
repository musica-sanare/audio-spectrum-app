"""Synthetic test signals. Tests never use real songs."""

import numpy as np

from audio_spectrum.audio import Audio

SAMPLE_RATE = 48000


def sine(frequency: float, seconds: float, amplitude: float = 1.0, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    t = np.arange(round(seconds * sample_rate)) / sample_rate
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def stereo(left: np.ndarray, right: np.ndarray | None = None, sample_rate: int = SAMPLE_RATE) -> Audio:
    right = left if right is None else right
    return Audio(samples=np.stack([left, right], axis=1), sample_rate=sample_rate)
