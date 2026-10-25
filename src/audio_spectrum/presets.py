"""Presets: how audio is analyzed and how the bands are drawn, loaded from TOML files.

Built-in presets ship as TOML files in `builtin_presets/`. Missing keys take the defaults below, which are the
`default` preset's values; unknown keys are errors.
"""

import tomllib
from importlib import resources
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Discriminator, Field, Tag, ValidationError

from audio_spectrum.analysis import AnalysisSettings
from audio_spectrum.errors import PresetError

SCHEMA_VERSION = 1
BUILTIN_PRESET_PACKAGE = "audio_spectrum.builtin_presets"


def parse_color(value: object) -> object:
    """Accept "#RRGGBB" (or "RRGGBB") as well as [r, g, b]."""
    if isinstance(value, str):
        digits = value.removeprefix("#")
        if len(digits) != 6:
            raise ValueError(f"expected a color like #0000FF, got {value!r}")
        try:
            return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            raise ValueError(f"expected a color like #0000FF, got {value!r}") from None
    return value


Channel = Annotated[int, Field(ge=0, le=255)]
Color = Annotated[tuple[Channel, Channel, Channel], BeforeValidator(parse_color)]

BLUE_BACK = (0, 0, 255)
GREEN_BACK = (0, 255, 0)
WHITE = (255, 255, 255)


class _Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FlatLook(_Settings):
    """Vertical lines or bars side by side, growing from a horizontal baseline."""

    kind: Literal["flat"] = "flat"
    margin_x: float = Field(0.04, ge=0.0, lt=0.5)
    """Empty space left and right, as a fraction of the frame width."""
    baseline_y: float = Field(0.5, ge=0.0, le=1.0)
    """Baseline position, as a fraction of the frame height from the top."""
    max_height: float = Field(0.3, gt=0.0, le=1.0)
    """Height of a full-scale band on one side of the baseline, as a fraction of the frame height."""
    mirror: bool = True
    """Grow both up and down from the baseline."""
    bar_fill: float = Field(0.5, gt=0.0, le=1.0)
    """Fraction of each band's slot covered by its line; the rest is the gap."""
    min_bar_width_px: float = Field(2.0, ge=0.0)
    min_height_px: float = Field(1.0, ge=0.0)
    """Every band is at least this tall on each side, so the baseline stays visible."""
    response: float = Field(1.6, gt=0.0)
    """Exponent applied to band values: above 1 keeps quiet bands low and lets peaks stand out."""


class PerspectiveLook(_Settings):
    """Thin boxes in a row seen through a tilted perspective camera, approximating the legacy Unity scene."""

    kind: Literal["perspective"] = "perspective"
    first_x: float = -15.0
    spacing: float = Field(0.1, gt=0.0)
    box_size: float = Field(0.105, gt=0.0)
    """Slightly wider than the spacing so neighboring boxes overlap and no anti-aliasing seams show between them."""
    depth: float = 10.0
    height_scale: float = Field(200.0, gt=0.0)
    camera_position: tuple[float, float, float] = (0.0, 6.0, -10.0)
    camera_pitch_degrees: float = Field(26.0, gt=-90.0, lt=90.0)
    vertical_fov_degrees: float = Field(60.0, gt=0.0, lt=180.0)


def _look_kind(value: object) -> str:
    """A [look] table without `kind` is a flat look."""
    if isinstance(value, dict):
        return value.get("kind", "flat")
    return getattr(value, "kind", "flat")


Look = Annotated[
    Annotated[FlatLook, Tag("flat")] | Annotated[PerspectiveLook, Tag("perspective")],
    Discriminator(_look_kind),
]


class Preset(_Settings):
    schema_version: Literal[1] = SCHEMA_VERSION
    name: str
    background: Color = BLUE_BACK
    foreground: Color = WHITE
    analysis: AnalysisSettings = AnalysisSettings()
    look: Look = FlatLook()


def builtin_preset_names() -> list[str]:
    files = resources.files(BUILTIN_PRESET_PACKAGE).iterdir()
    return sorted(entry.name.removesuffix(".toml") for entry in files if entry.name.endswith(".toml"))


def builtin_preset_text(name: str) -> str:
    if name not in builtin_preset_names():
        raise PresetError(f"unknown preset {name!r}; built-in presets: {', '.join(builtin_preset_names())}")
    return resources.files(BUILTIN_PRESET_PACKAGE).joinpath(f"{name}.toml").read_text(encoding="utf-8")


def load_preset(name_or_path: str | Path) -> Preset:
    """Load a built-in preset by name, or a preset file by path (anything ending in .toml or containing a slash)."""
    text = str(name_or_path)
    if isinstance(name_or_path, Path) or text.endswith(".toml") or "/" in text:
        path = Path(name_or_path)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as error:
            raise PresetError(f"cannot read preset file {path}: {error.strerror}") from None
        return parse_preset(source, origin=str(path))
    return parse_preset(builtin_preset_text(text), origin=f"built-in preset {text!r}")


def parse_preset(source: str, origin: str = "preset") -> Preset:
    try:
        data = tomllib.loads(source)
    except tomllib.TOMLDecodeError as error:
        raise PresetError(f"{origin} is not valid TOML: {error}") from None
    try:
        return Preset.model_validate(data)
    except ValidationError as error:
        raise PresetError(f"{origin} is invalid:\n{_describe(error)}") from None


def _describe(error: ValidationError) -> str:
    lines = []
    for problem in error.errors():
        location = ".".join(str(part) for part in problem["loc"]) or "(top level)"
        lines.append(f"  {location}: {problem['msg']}")
    return "\n".join(lines)
