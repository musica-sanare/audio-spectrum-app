"""Turn one frame of band values into polygons in pixel coordinates.

Geometry is independent of the drawing library: every look produces quads with shape (count, 4, 2) as (x, y) pixel
coordinates, and a raster backend fills them.
"""

import math
from dataclasses import dataclass

import numpy as np

from audio_spectrum.presets import Color, Fill, FlatLook, Look, PerspectiveLook


@dataclass(frozen=True)
class Gradient:
    """A linear gradient in pixel coordinates, independent of the drawing library."""

    start: tuple[float, float]
    end: tuple[float, float]
    colors: tuple[Color, ...]
    mirror: bool = False
    """Mirror the gradient on the other side of `start` (for bars that grow both ways from the baseline)."""


def quads_for(look: Look, values: np.ndarray, width: int, height: int) -> np.ndarray:
    if isinstance(look, FlatLook):
        return flat_quads(look, values, width, height)
    return perspective_quads(look, values, width, height)


def flat_quads(look: FlatLook, values: np.ndarray, width: int, height: int) -> np.ndarray:
    num_bands = len(values)
    left = look.margin_x * width
    slot = (width - 2 * left) / num_bands
    bar_width = max(slot * look.bar_fill, look.min_bar_width_px)
    centers = left + slot * (np.arange(num_bands) + 0.5)
    x0 = centers - bar_width / 2
    x1 = centers + bar_width / 2

    extent = look.max_height * height * np.clip(values, 0.0, 1.0) ** look.response
    extent = np.maximum(extent, look.min_height_px)
    baseline = look.baseline_y * height
    if look.style == "blocks":
        return _blocks(look, x0, x1, extent, baseline, height)
    top = baseline - extent
    bottom = baseline + extent if look.mirror else np.full(num_bands, baseline)
    return _rectangles(x0, top, x1, bottom)


def _blocks(
    look: FlatLook, x0: np.ndarray, x1: np.ndarray, extent: np.ndarray, baseline: float, height: int
) -> np.ndarray:
    """Split each bar into whole segments counted outward from the baseline; a segment the bar does not fully reach
    is not drawn. Mirrored segments start half a gap away from the baseline so the two halves stay apart."""
    pitch = look.block_height_px + look.block_gap_px
    offset = look.block_gap_px / 2 if look.mirror else 0.0
    counts = np.floor((extent - offset + look.block_gap_px) / pitch).astype(np.int64)
    max_count = max(int(np.floor((look.max_height * height - offset + look.block_gap_px) / pitch)), 0)
    counts = np.clip(counts, 0, max_count)
    bands, segments = np.nonzero(np.arange(max_count)[None, :] < counts[:, None])
    near = baseline - offset - segments * pitch
    far = near - look.block_height_px
    quads = _rectangles(x0[bands], far, x1[bands], near)
    if look.mirror:
        quads = np.concatenate([quads, _rectangles(x0[bands], 2 * baseline - near, x1[bands], 2 * baseline - far)])
    return quads


def gradient_for(look: Look, fill: Fill, width: int, height: int) -> Gradient | None:
    """The gradient of a fill on a flat look, or None for a solid fill."""
    if fill.mode == "solid":
        return None
    if fill.mode == "frequency":
        left = look.margin_x * width
        return Gradient((left, 0.0), (width - left, 0.0), fill.colors)
    baseline = look.baseline_y * height
    return Gradient((0.0, baseline), (0.0, baseline - look.max_height * height), fill.colors, mirror=look.mirror)


def perspective_quads(look: PerspectiveLook, values: np.ndarray, width: int, height: int) -> np.ndarray:
    """Project each box (centered on the baseline, growing up and down like a scaled Unity cube) and return the
    outline of its front face and top face as one quad: the box is thin enough that this covers its silhouette."""
    num_bands = len(values)
    x = look.first_x + look.spacing * np.arange(num_bands)
    half_height = values * look.height_scale / 2
    half_size = look.box_size / 2
    near = look.depth - half_size

    # Corners: bottom-left and bottom-right on the front face, top-right and top-left on the back face, which
    # together outline the box as seen from above.
    corners = np.stack(
        [
            np.stack([x - half_size, -half_height, np.full(num_bands, near)], axis=1),
            np.stack([x + half_size, -half_height, np.full(num_bands, near)], axis=1),
            np.stack([x + half_size, half_height, np.full(num_bands, near + look.box_size)], axis=1),
            np.stack([x - half_size, half_height, np.full(num_bands, near + look.box_size)], axis=1),
        ],
        axis=1,
    )
    return _project(look, corners, width, height)


def _project(look: PerspectiveLook, points: np.ndarray, width: int, height: int) -> np.ndarray:
    """Project world points with Unity's conventions: left-handed, y up, camera looking along +z, positive pitch
    looking down, vertical field of view."""
    pitch = math.radians(look.camera_pitch_degrees)
    right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, math.cos(pitch), math.sin(pitch)])
    forward = np.array([0.0, -math.sin(pitch), math.cos(pitch)])
    relative = points - np.asarray(look.camera_position)
    camera_x = relative @ right
    camera_y = relative @ up
    camera_z = relative @ forward

    focal = 1.0 / math.tan(math.radians(look.vertical_fov_degrees) / 2)
    aspect = width / height
    ndc_x = camera_x * focal / (aspect * camera_z)
    ndc_y = camera_y * focal / camera_z
    return np.stack([(ndc_x + 1) / 2 * width, (1 - ndc_y) / 2 * height], axis=-1)


def _rectangles(x0: np.ndarray, y0: np.ndarray, x1: np.ndarray, y1: np.ndarray) -> np.ndarray:
    return np.stack(
        [np.stack([x0, y0], axis=1), np.stack([x1, y0], axis=1), np.stack([x1, y1], axis=1), np.stack([x0, y1], axis=1)],
        axis=1,
    )
