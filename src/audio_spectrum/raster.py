"""Raster backends: fill anti-aliased quads into an RGB frame."""

from typing import Protocol

import numpy as np
import skia

from audio_spectrum.geometry import Gradient
from audio_spectrum.presets import Color


class Rasterizer(Protocol):
    name: str

    def draw(
        self, quads: np.ndarray, background: Color | None, foreground: Color, gradient: Gradient | None = None
    ) -> np.ndarray:
        """Return a frame with shape (height, width, 3), uint8 RGB, or (height, width, 4) RGBA with straight alpha
        when the background is None (transparent). A gradient, if given, replaces the foreground."""
        ...


class SkiaRasterizer:
    name = "skia"

    def __init__(self, width: int, height: int):
        self._pixels = np.zeros((height, width, 4), dtype=np.uint8)
        self._surface = skia.Surface(self._pixels, colorType=skia.kRGBA_8888_ColorType)
        self._paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style)

    def draw(
        self, quads: np.ndarray, background: Color | None, foreground: Color, gradient: Gradient | None = None
    ) -> np.ndarray:
        path = skia.Path()
        for quad in quads.tolist():
            path.addPoly([skia.Point(x, y) for x, y in quad], True)
        self._paint.setColor(skia.Color(*foreground))
        paint = self._paint
        if gradient is not None:
            paint = skia.Paint(self._paint)
            paint.setShader(_shader(gradient))
        with self._surface as canvas:
            # The surface stores straight (unpremultiplied) alpha, as ffmpeg's rgba input and PNG expect.
            canvas.clear(skia.ColorTRANSPARENT if background is None else skia.Color(*background))
            canvas.drawPath(path, paint)
        if background is None:
            return self._pixels.copy()
        return self._pixels[:, :, :3].copy()


def _shader(gradient: Gradient) -> skia.Shader:
    return skia.GradientShader.MakeLinear(
        [skia.Point(*gradient.start), skia.Point(*gradient.end)],
        [skia.Color(*color) for color in gradient.colors],
        None,
        skia.TileMode.kMirror if gradient.mirror else skia.TileMode.kClamp,
    )


RASTERIZERS = {"skia": SkiaRasterizer}
