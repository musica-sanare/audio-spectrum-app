"""Presets: how audio is analyzed and how the bands are drawn, loaded from TOML files.

Built-in presets ship as TOML files in `builtin_presets/`. Missing keys take the defaults below, which are the
`default` preset's values; unknown keys are errors.
"""

import math
import tomllib
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Discriminator, Field, Tag, ValidationError, model_validator

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


BarStyle = Literal["bars", "blocks"]
FillMode = Literal["solid", "frequency", "height"]

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
    style: BarStyle = "bars"
    """"bars": one solid line or bar per band; "blocks": each bar split into segments, like an LED meter."""
    block_height_px: float = Field(8.0, gt=0.0)
    """Blocks: height of one segment. A segment shows only once the bar reaches its full height."""
    block_gap_px: float = Field(3.0, ge=0.0)
    """Blocks: gap between segments, and around the baseline when mirrored."""


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


class Fill(_Settings):
    """How the lines are colored: the foreground color, or a gradient."""

    mode: FillMode = "solid"
    """"solid": the foreground color; "frequency": a gradient from the left edge to the right edge; "height": a gradient
    from the baseline to a full-scale tip (flat look only)."""
    colors: tuple[Color, ...] = ()
    """Gradient stops, evenly spaced: at least two colors when the mode is not "solid"."""


class Effects(_Settings):
    """Effects drawn with the lines. All off by default."""

    glow_radius_px: float = Field(0.0, ge=0.0, le=200.0)
    """How far a soft halo spreads around the lines, in pixels; 0 turns the glow off. The halo mixes with a key-color
    background, so check keying, or use a transparent background."""
    glow_strength: float = Field(1.0, gt=0.0, le=1.0)
    """Opacity of the halo."""


class Preset(_Settings):
    schema_version: Literal[1] = SCHEMA_VERSION
    name: str
    background: Color = BLUE_BACK
    foreground: Color = WHITE
    analysis: AnalysisSettings = AnalysisSettings()
    look: Look = FlatLook()
    fill: Fill = Fill()
    fx: Effects = Effects()

    @model_validator(mode="after")
    def _check(self) -> "Preset":
        if self.fill.mode != "solid":
            if len(self.fill.colors) < 2:
                raise ValueError(f"fill.colors needs at least two colors for the {self.fill.mode!r} gradient")
            if not isinstance(self.look, FlatLook):
                raise ValueError("fill gradients need the flat look")
        return self


REFERENCE_WIDTH = 1920
THIN_LINE_PX = 4.0
MAX_READABLE_BLOCK_BANDS = 128


def preset_warnings(preset: Preset) -> list[str]:
    """Problems that do not make a preset invalid but are likely to key or encode badly. Heuristics, checked against
    the preset's own background."""
    warnings = []
    colors = preset.fill.colors if preset.fill.mode != "solid" else (preset.foreground,)
    background = _chroma(preset.background)
    for color in colors:
        if _close_to_key(_chroma(color), background):
            warnings.append(
                f"line color {_hex(color)} is close to the background {_hex(preset.background)}; "
                "a chroma key may remove it"
            )
    look = preset.look
    if isinstance(look, FlatLook):
        slot = REFERENCE_WIDTH * (1 - 2 * look.margin_x) / preset.analysis.bands
        line_width = max(slot * look.bar_fill, look.min_bar_width_px)
        if line_width < THIN_LINE_PX and any(math.hypot(*_chroma(color)) > 0.1 for color in colors):
            warnings.append(
                f"lines are about {line_width:.1f} px wide at 1080p; thin colored lines lose much of their color in "
                "H.264 (use --codec prores4444, or fewer bands or a larger look.bar_fill)"
            )
        if look.style == "blocks" and preset.analysis.bands > MAX_READABLE_BLOCK_BANDS:
            warnings.append(f"blocks with {preset.analysis.bands} bands are hard to read; 32 to 96 bands work best")
    if preset.fx.glow_radius_px > 0:
        warnings.append(
            f"the glow mixes with the background {_hex(preset.background)}, so a chroma key may leave a colored fringe "
            "or cut the halo; check keying in your editor, or render with --background transparent --codec prores4444"
        )
    return warnings


def _chroma(color: tuple[int, int, int]) -> tuple[float, float]:
    """BT.709 (Cb, Cr) of an RGB color, each in about [-0.5, 0.5]."""
    red, green, blue = (channel / 255 for channel in color)
    luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return (blue - luma) / 1.8556, (red - luma) / 1.5748


def _close_to_key(color: tuple[float, float], key: tuple[float, float]) -> bool:
    """True when a keyer would likely treat the color as the key color: a similar hue with noticeable saturation."""
    key_strength = math.hypot(*key)
    strength = math.hypot(*color)
    if key_strength < 0.2 or strength < 0.2 * key_strength:
        return False
    cosine = (color[0] * key[0] + color[1] * key[1]) / (strength * key_strength)
    return cosine > math.cos(math.radians(45))


def _hex(color: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in color)


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


def override_preset(preset: Preset, assignments: Iterable[str]) -> Preset:
    """Apply "dotted.key=value" assignments and validate the result like a preset file.

    Values use TOML syntax (`0.4`, `true`, `["#FFFFFF", "#00FFFF"]`); a value that is not valid TOML is taken as a
    plain string, so `analysis.channel=left` and `background=#00FF00` need no quotes.
    """
    assignments = list(assignments)
    if not assignments:
        return preset
    data = preset.model_dump()
    for assignment in assignments:
        key, separator, text = assignment.partition("=")
        key = key.strip()
        if not separator or not key:
            raise PresetError(f"--set expects KEY=VALUE, got {assignment!r}")
        if key == "look.kind":
            raise PresetError("--set cannot change look.kind; start from a preset with the look you want")
        *parents, leaf = key.split(".")
        table = data
        for part in parents:
            table = table.get(part) if isinstance(table, dict) else None
            if not isinstance(table, dict):
                raise PresetError(f"--set {key}: {part!r} is not a preset table")
        table[leaf] = _toml_value(text.strip())
    try:
        return Preset.model_validate(data)
    except ValidationError as error:
        raise PresetError(f"preset with --set overrides is invalid:\n{_describe(error)}") from None


def _toml_value(text: str) -> object:
    try:
        return tomllib.loads(f"value = {text}")["value"]
    except tomllib.TOMLDecodeError:
        return text


def _describe(error: ValidationError) -> str:
    lines = []
    for problem in error.errors():
        location = ".".join(str(part) for part in problem["loc"]) or "(top level)"
        lines.append(f"  {location}: {problem['msg']}")
    return "\n".join(lines)
