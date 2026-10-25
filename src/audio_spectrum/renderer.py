"""Render frames from band values with a preset."""

import numpy as np

from audio_spectrum.geometry import gradient_for, quads_for
from audio_spectrum.presets import Preset
from audio_spectrum.raster import RASTERIZERS, Glow, Rasterizer


class FrameRenderer:
    def __init__(self, preset: Preset, width: int, height: int, rasterizer: str = "skia", transparent: bool = False):
        self.preset = preset
        self.transparent = transparent
        self.width = width
        self.height = height
        self._rasterizer: Rasterizer = RASTERIZERS[rasterizer](width, height)
        self._gradient = gradient_for(preset.look, preset.fill, width, height)
        fx = preset.fx
        self._glow = Glow(fx.glow_radius_px, fx.glow_strength) if fx.glow_radius_px > 0 else None

    def render(self, values: np.ndarray) -> np.ndarray:
        """Render one frame of band values. Returns (height, width, 3) uint8 RGB, or (height, width, 4) RGBA with a
        transparent background."""
        quads = quads_for(self.preset.look, values, self.width, self.height)
        quads = quads[_visible(quads, self.width, self.height)]
        background = None if self.transparent else self.preset.background
        return self._rasterizer.draw(quads, background, self.preset.foreground, self._gradient, self._glow)


def _visible(quads: np.ndarray, width: int, height: int) -> np.ndarray:
    xs = quads[:, :, 0]
    ys = quads[:, :, 1]
    return (xs.max(axis=1) >= 0) & (xs.min(axis=1) <= width) & (ys.max(axis=1) >= 0) & (ys.min(axis=1) <= height)
