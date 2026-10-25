"""Built-in presets: how audio is analyzed and how the bands are drawn."""

import math
from dataclasses import dataclass, field
from typing import Literal

from audio_spectrum.analysis import AnalysisSettings

Color = tuple[int, int, int]

BLUE_BACK: Color = (0, 0, 255)
GREEN_BACK: Color = (0, 255, 0)
WHITE: Color = (255, 255, 255)


@dataclass(frozen=True)
class FlatLook:
    """Vertical lines or bars side by side, growing from a horizontal baseline."""

    kind: Literal["flat"] = "flat"
    margin_x: float = 0.04
    """Empty space left and right, as a fraction of the frame width."""
    baseline_y: float = 0.5
    """Baseline position, as a fraction of the frame height from the top."""
    max_height: float = 0.3
    """Height of a full-scale band on one side of the baseline, as a fraction of the frame height."""
    mirror: bool = True
    """Grow both up and down from the baseline."""
    bar_fill: float = 0.5
    """Fraction of each band's slot covered by its line; the rest is the gap."""
    min_bar_width_px: float = 2.0
    min_height_px: float = 1.0
    """Every band is at least this tall on each side, so the baseline stays visible."""
    response: float = 1.6
    """Exponent applied to band values: above 1 keeps quiet bands low and lets peaks stand out."""


@dataclass(frozen=True)
class PerspectiveLook:
    """Thin boxes in a row seen through a tilted perspective camera, approximating the legacy Unity scene."""

    kind: Literal["perspective"] = "perspective"
    first_x: float = -15.0
    spacing: float = 0.1
    box_size: float = 0.105
    """Slightly wider than the spacing so neighboring boxes overlap and no anti-aliasing seams show between them."""
    depth: float = 10.0
    height_scale: float = 200.0
    camera_position: tuple[float, float, float] = (0.0, 6.0, -10.0)
    camera_pitch_degrees: float = 26.0
    vertical_fov_degrees: float = 60.0


Look = FlatLook | PerspectiveLook


@dataclass(frozen=True)
class Preset:
    name: str
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)
    look: Look = field(default_factory=FlatLook)
    background: Color = BLUE_BACK
    foreground: Color = WHITE


PRESETS: dict[str, Preset] = {
    "default": Preset(
        name="default",
        analysis=AnalysisSettings(num_bands=512, db_floor=-48.0, tilt_db_per_octave=3.0),
        look=FlatLook(),
    ),
    "unity-classic": Preset(
        name="unity-classic",
        analysis=AnalysisSettings(
            fft_size=4096,
            num_bands=2048,
            frequency_scale="linear",
            min_frequency=0.0,
            max_frequency=math.inf,
            magnitude_scale="linear",
            gain=0.1,
            channel="left",
            attack_seconds=0.0,
            release_seconds=0.0,
        ),
        look=PerspectiveLook(),
    ),
}
