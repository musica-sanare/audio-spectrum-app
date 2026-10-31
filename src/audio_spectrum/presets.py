"""Presets: how audio is analyzed and how the bands are drawn, loaded from TOML files.

Built-in presets ship as TOML files in `builtin_presets/`. Missing keys take the defaults below, which are the
`default` preset's values; unknown keys are errors.
"""

import json
import math
import os
import tomllib
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    PlainSerializer,
    Tag,
    ValidationError,
    WithJsonSchema,
    model_validator,
)

from audio_spectrum.analysis import AnalysisSettings
from audio_spectrum.errors import OutputExistsError, PresetError

SCHEMA_VERSION = 1
BUILTIN_PRESET_PACKAGE = "audio_spectrum.builtin_presets"
USER_PRESET_ENVIRONMENT = "AUDIO_SPECTRUM_PRESET_DIR"
DEFAULT_USER_PRESET_FOLDER = "~/Library/Application Support/audio-spectrum/presets"
MAX_NAME_LENGTH = 100


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
Color = Annotated[
    tuple[Channel, Channel, Channel],
    BeforeValidator(parse_color),
    # Written as "#RRGGBB" in JSON and in the JSON schema, as in preset files.
    PlainSerializer(lambda color: "#" + "".join(f"{channel:02X}" for channel in color), when_used="json"),
    WithJsonSchema({"type": "string", "format": "color", "pattern": "^#[0-9A-Fa-f]{6}$"}),
]

BLUE_BACK = (0, 0, 255)
GREEN_BACK = (0, 255, 0)
WHITE = (255, 255, 255)


class _Settings(BaseModel):
    # JSON has no infinity, so `inf` (max_frequency) is written as "Infinity", which validation reads back.
    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True, ser_json_inf_nan="strings")


class FlatLook(_Settings):
    """Vertical lines or bars side by side, growing from a horizontal baseline."""

    kind: Literal["flat"] = "flat"
    """The look: "flat" lines or bars, or "perspective" as in the legacy Unity scene."""
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
    """Lines are never thinner than this, in pixels."""
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
    """The look: "flat" lines or bars, or "perspective" as in the legacy Unity scene."""
    first_x: float = -15.0
    """Position of the first box along the row, in scene units."""
    spacing: float = Field(0.1, gt=0.0)
    """Distance between neighboring boxes, in scene units."""
    box_size: float = Field(0.105, gt=0.0)
    """Slightly wider than the spacing so neighboring boxes overlap and no anti-aliasing seams show between them."""
    depth: float = 10.0
    """Distance of the row from the scene origin along the view direction, in scene units."""
    height_scale: float = Field(200.0, gt=0.0)
    """Box height for a band value of 1, in scene units."""
    camera_position: tuple[float, float, float] = (0.0, 6.0, -10.0)
    """Camera position (x, y, z) in scene units."""
    camera_pitch_degrees: float = Field(26.0, gt=-90.0, lt=90.0)
    """How far the camera looks down, in degrees."""
    vertical_fov_degrees: float = Field(60.0, gt=0.0, lt=180.0)
    """Vertical field of view of the camera, in degrees."""


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
    """Version of the preset file format."""
    name: str
    """Name of the preset."""
    background: Color = BLUE_BACK
    """Background color, usually the key color: pure blue or green."""
    foreground: Color = WHITE
    """Color of the lines when fill.mode is "solid"."""
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


def user_preset_folder() -> Path:
    """Where saved presets live: the folder in $AUDIO_SPECTRUM_PRESET_DIR, or
    ~/Library/Application Support/audio-spectrum/presets. It may not exist yet."""
    return Path(os.environ.get(USER_PRESET_ENVIRONMENT) or DEFAULT_USER_PRESET_FOLDER).expanduser()


def user_preset_names() -> list[str]:
    """Names of the presets in the user folder. Files named like a built-in preset are left out: built-in names are
    reserved, so `--preset default` always means the built-in one (see `shadowed_user_preset_names`)."""
    builtin = set(builtin_preset_names())
    return [name for name in _user_preset_stems() if name not in builtin]


def shadowed_user_preset_names() -> list[str]:
    """User preset files that are ignored because a built-in preset has the same name."""
    builtin = set(builtin_preset_names())
    return [name for name in _user_preset_stems() if name in builtin]


def _user_preset_stems() -> list[str]:
    folder = user_preset_folder()
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.toml") if not path.name.startswith("."))


def save_user_preset(preset: Preset, overwrite: bool = False) -> Path:
    """Write the preset into the user folder as `<name>.toml`, with only the keys that differ from `default`, and
    return its path. Built-in names and names that cannot be file names raise PresetError; an existing file raises
    OutputExistsError unless `overwrite`."""
    _check_user_preset_name(preset.name)
    folder = user_preset_folder()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{preset.name}.toml"
    if path.exists() and not overwrite:
        raise OutputExistsError(f"user preset {preset.name!r} already exists ({path})")
    partial = path.with_name(f".{path.name}.partial-{os.getpid()}")
    try:
        partial.write_text(preset_to_toml(preset), encoding="utf-8")
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
    return path


def _check_user_preset_name(name: str) -> None:
    if name in builtin_preset_names():
        raise PresetError(f"{name!r} is the name of a built-in preset; choose another name")
    if (
        not name.strip() or name != name.strip() or len(name) > MAX_NAME_LENGTH or name.startswith(".")
        or name.endswith(".toml") or any(character in name for character in "/\\:")
        or any(ord(character) < 32 for character in name)
    ):
        raise PresetError(
            f"{name!r} cannot be a preset name: use up to {MAX_NAME_LENGTH} characters without slashes, colons, "
            "leading or trailing spaces, or a leading dot"
        )


def load_preset(name_or_path: str | Path) -> Preset:
    """Load a preset by name, built-in first, then from the user folder; or a preset file by path (anything ending
    in .toml or containing a slash)."""
    text = str(name_or_path)
    if isinstance(name_or_path, Path) or text.endswith(".toml") or "/" in text:
        path = Path(name_or_path)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as error:
            raise PresetError(f"cannot read preset file {path}: {error.strerror}") from None
        return parse_preset(source, origin=str(path))
    if text in builtin_preset_names():
        return parse_preset(builtin_preset_text(text), origin=f"built-in preset {text!r}")
    if text in user_preset_names():
        path = user_preset_folder() / f"{text}.toml"
        return parse_preset(path.read_text(encoding="utf-8"), origin=f"user preset {text!r} ({path})")
    user = user_preset_names()
    raise PresetError(
        f"unknown preset {text!r}; built-in presets: {', '.join(builtin_preset_names())}"
        + (f"; user presets: {', '.join(user)}" if user else "")
    )


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


COLOR_KEYS = {"background", "foreground", "fill.colors"}


def preset_schema() -> dict:
    """JSON schema of a preset, for building forms: types, ranges, defaults and the description of every key. Colors
    are "#RRGGBB" strings, as in preset files."""
    return Preset.model_json_schema(mode="serialization")


def preset_to_toml(preset: Preset, full: bool = False) -> str:
    """The preset as a TOML file that `load_preset` reads back to an equal preset. By default only the keys that differ
    from the default preset are written, plus `schema_version` and `name`; `full` writes every key."""
    data = preset.model_dump()
    if not full:
        reference = Preset(name=preset.name, look=type(preset.look)()).model_dump()
        data = {
            key: _changed(value, reference[key]) if isinstance(value, dict) else value
            for key, value in data.items()
            if key in ("schema_version", "name") or isinstance(value, dict) or value != reference[key]
        }
        if preset.look.kind != "flat":
            data["look"] = {"kind": preset.look.kind, **data["look"]}
    lines = [] if full else ["# Keys not listed take the default preset's values (see `presets show default`)."]
    lines += [f"{key} = {_format_toml(value, key)}" for key, value in data.items() if not isinstance(value, dict)]
    for table, values in data.items():
        if isinstance(values, dict) and values:
            lines += ["", f"[{table}]"]
            lines += [f"{key} = {_format_toml(value, f'{table}.{key}')}" for key, value in values.items()]
    return "\n".join(lines) + "\n"


def _changed(values: dict, reference: dict) -> dict:
    return {key: value for key, value in values.items() if value != reference[key]}


def _format_toml(value: object, key: str) -> str:
    if key in COLOR_KEYS:
        colors = [_hex(color) for color in value] if key == "fill.colors" else _hex(value)
        return _format_toml(colors, "")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        # A JSON string is a valid TOML basic string.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_toml(item, "") for item in value) + "]"
    raise TypeError(f"cannot write {key or 'value'} of type {type(value).__name__} as TOML")


def _describe(error: ValidationError) -> str:
    lines = []
    for problem in error.errors():
        location = ".".join(str(part) for part in problem["loc"]) or "(top level)"
        lines.append(f"  {location}: {problem['msg']}")
    return "\n".join(lines)
