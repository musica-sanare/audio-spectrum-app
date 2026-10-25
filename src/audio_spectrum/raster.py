"""Raster backends: fill anti-aliased quads into an RGB frame."""

from typing import Protocol

import numpy as np
import skia

from audio_spectrum.presets import Color


class Rasterizer(Protocol):
    name: str

    def draw(self, quads: np.ndarray, background: Color, foreground: Color) -> np.ndarray:
        """Return a frame with shape (height, width, 3), uint8 RGB."""
        ...


class SkiaRasterizer:
    name = "skia"

    def __init__(self, width: int, height: int):
        self._pixels = np.zeros((height, width, 4), dtype=np.uint8)
        self._surface = skia.Surface(self._pixels, colorType=skia.kRGBA_8888_ColorType)
        self._paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style)

    def draw(self, quads: np.ndarray, background: Color, foreground: Color) -> np.ndarray:
        path = skia.Path()
        for quad in quads.tolist():
            path.addPoly([skia.Point(x, y) for x, y in quad], True)
        self._paint.setColor(skia.Color(*foreground))
        with self._surface as canvas:
            canvas.clear(skia.Color(*background))
            canvas.drawPath(path, self._paint)
        return self._pixels[:, :, :3].copy()


RASTERIZERS = {"skia": SkiaRasterizer}
