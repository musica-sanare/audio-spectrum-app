import math

import pytest

from audio_spectrum.analysis import AnalysisSettings
from audio_spectrum.cli import main
from audio_spectrum.errors import PresetError
from audio_spectrum.presets import (
    FlatLook,
    PerspectiveLook,
    Preset,
    builtin_preset_names,
    builtin_preset_text,
    load_preset,
    override_preset,
    parse_preset,
    preset_warnings,
)


def test_builtin_presets_are_listed():
    assert builtin_preset_names() == ["bars", "blocks", "default", "unity-classic"]


def test_default_preset_file_matches_the_model_defaults():
    # Missing keys take the model defaults, so the default file and an empty preset must describe the same look.
    assert load_preset("default") == Preset(name="default")


def test_unity_classic_loads_its_perspective_look():
    preset = load_preset("unity-classic")
    assert isinstance(preset.look, PerspectiveLook)
    assert preset.analysis.bands == 2048
    assert preset.analysis.channel == "left"
    assert math.isinf(preset.analysis.max_frequency)


def test_preset_file_by_path_with_partial_keys(tmp_path):
    path = tmp_path / "mine.toml"
    path.write_text('name = "mine"\nbackground = "#00FF00"\n[analysis]\nbands = 64\n[look]\nmirror = false\n')
    preset = load_preset(path)
    assert preset.background == (0, 255, 0)
    assert preset.analysis.bands == 64
    assert preset.analysis.db_floor == AnalysisSettings().db_floor
    assert preset.look == FlatLook(mirror=False)


def test_path_given_as_string_is_read_as_a_file(tmp_path):
    path = tmp_path / "mine.toml"
    path.write_text('name = "mine"\n')
    assert load_preset(str(path)).name == "mine"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ('name = "x"\n[analysis]\nbandz = 64\n', "analysis.bandz"),
        ('name = "x"\n[analysis]\nbands = "many"\n', "analysis.bands"),
        ('name = "x"\n[analysis]\nbands = 0\n', "analysis.bands"),
        ('name = "x"\n[analysis]\nfft_size = 1000\n', "power of two"),
        ('name = "x"\n[analysis]\nmin_frequency = 500.0\nmax_frequency = 100.0\n', "max_frequency"),
        ('name = "x"\nbackground = "blue"\n', "background"),
        ('name = "x"\n[look]\nkind = "sphere"\n', "look"),
        ('name = "x"\nschema_version = 2\n', "schema_version"),
        ("[analysis]\n", "name"),
        ('name = "x"\n[analysis\n', "not valid TOML"),
    ],
)
def test_invalid_presets_name_the_problem(source, message):
    with pytest.raises(PresetError, match=message):
        parse_preset(source)


def test_unknown_builtin_name_lists_the_available_presets():
    with pytest.raises(PresetError, match="default, unity-classic"):
        load_preset("nonexistent")


def test_missing_preset_file_is_a_preset_error(tmp_path):
    with pytest.raises(PresetError, match="cannot read"):
        load_preset(tmp_path / "missing.toml")


def test_cli_presets_list_and_show(capsys):
    assert main(["presets", "list"]) == 0
    assert capsys.readouterr().out.split() == ["bars", "blocks", "default", "unity-classic"]
    assert main(["presets", "show", "default"]) == 0
    assert capsys.readouterr().out == builtin_preset_text("default")


def test_cli_presets_check(tmp_path, capsys):
    good = tmp_path / "good.toml"
    good.write_text('name = "good"\n')
    bad = tmp_path / "bad.toml"
    bad.write_text('name = "bad"\n[look]\nmargin_x = 0.9\n')
    assert main(["presets", "check", str(good)]) == 0
    assert "valid preset 'good'" in capsys.readouterr().out
    assert main(["presets", "check", str(bad)]) == 2
    assert "look.flat.margin_x" in capsys.readouterr().err


def test_cli_render_with_an_invalid_preset_is_a_usage_error(tmp_path, capsys):
    audio = tmp_path / "missing.wav"
    assert main(["render", str(audio), "--preset", "nonexistent"]) == 2
    assert "unknown preset" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (["fill.mode=frequency"], "at least two colors"),
        (["fill.mode=rainbow"], "fill.mode"),
        (["fill.colors=[\"#FF0000\", \"red\"]"], "fill.colors"),
    ],
)
def test_invalid_fills_are_rejected(overrides, message):
    with pytest.raises(PresetError, match=message):
        override_preset(load_preset("default"), overrides)


def test_gradients_need_the_flat_look():
    with pytest.raises(PresetError, match="flat look"):
        override_preset(load_preset("unity-classic"), ["fill.mode=height", "fill.colors=[\"#FFFFFF\", \"#00FFFF\"]"])


@pytest.mark.parametrize("name", builtin_preset_names())
def test_builtin_presets_have_no_warnings(name):
    assert preset_warnings(load_preset(name)) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (["foreground=#8080FF"], "close to the background #0000FF"),
        (["foreground=#8000FF"], "close to the background"),
        (["background=#00FF00", "foreground=#40C040"], "close to the background #00FF00"),
        (["fill.mode=frequency", "fill.colors=[\"#FFFFFF\", \"#6060FF\"]"], "#6060FF is close"),
        (["foreground=#FF00C8"], "thin colored lines"),
        (["look.style=blocks"], "blocks with 512 bands"),
    ],
)
def test_risky_presets_get_warnings(overrides, expected):
    warnings = preset_warnings(override_preset(load_preset("default"), overrides))
    assert any(expected in warning for warning in warnings), warnings


@pytest.mark.parametrize(
    "overrides",
    [
        ["background=#00FF00"],
        ["foreground=#FFE000"] + ["analysis.bands=64", "look.bar_fill=0.8"],
        ["foreground=#00FFFF", "analysis.bands=64"],
        ["foreground=#C0C0C0"],
    ],
)
def test_safe_presets_get_no_warnings(overrides):
    assert preset_warnings(override_preset(load_preset("default"), overrides)) == []


def test_presets_check_prints_warnings_on_stderr_and_still_succeeds(tmp_path, capsys):
    path = tmp_path / "pale.toml"
    path.write_text('name = "pale"\nforeground = "#8080FF"\n')
    assert main(["presets", "check", str(path)]) == 0
    captured = capsys.readouterr()
    assert "valid preset 'pale'" in captured.out
    assert "warning: line color #8080FF is close to the background #0000FF" in captured.err
