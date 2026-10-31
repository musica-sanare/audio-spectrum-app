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
    preset_schema,
    preset_to_toml,
    preset_warnings,
)


def test_builtin_presets_are_listed():
    assert builtin_preset_names() == ["bars", "blocks", "default", "glow", "unity-classic"]


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
    with pytest.raises(PresetError, match="bars, blocks, default, glow, unity-classic"):
        load_preset("nonexistent")


def test_missing_preset_file_is_a_preset_error(tmp_path):
    with pytest.raises(PresetError, match="cannot read"):
        load_preset(tmp_path / "missing.toml")


def test_cli_presets_list_and_show(capsys):
    assert main(["presets", "list"]) == 0
    assert capsys.readouterr().out.split() == ["bars", "blocks", "default", "glow", "unity-classic"]
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


@pytest.mark.parametrize("overrides", [["fx.glow_radius_px=-1"], ["fx.glow_radius_px=500"], ["fx.glow_strength=0"],
                                       ["fx.glow_strength=1.5"], ["fx.halo=1"]])
def test_invalid_effects_are_rejected(overrides):
    with pytest.raises(PresetError, match="fx"):
        override_preset(load_preset("default"), overrides)


def test_gradients_need_the_flat_look():
    with pytest.raises(PresetError, match="flat look"):
        override_preset(load_preset("unity-classic"), ["fill.mode=height", "fill.colors=[\"#FFFFFF\", \"#00FFFF\"]"])


@pytest.mark.parametrize("name", builtin_preset_names())
def test_builtin_presets_warn_only_about_glow(name):
    warnings = preset_warnings(load_preset(name))
    assert warnings == ([] if name != "glow" else [warnings[0]])
    if name == "glow":
        assert "the glow mixes with the background #0000FF" in warnings[0]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (["foreground=#8080FF"], "close to the background #0000FF"),
        (["foreground=#8000FF"], "close to the background"),
        (["background=#00FF00", "foreground=#40C040"], "close to the background #00FF00"),
        (["fill.mode=frequency", "fill.colors=[\"#FFFFFF\", \"#6060FF\"]"], "#6060FF is close"),
        (["foreground=#FF00C8"], "thin colored lines"),
        (["look.style=blocks"], "blocks with 512 bands"),
        (["background=#00FF00", "fx.glow_radius_px=12"], "glow mixes with the background #00FF00"),
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


def schema_leaves(schema: dict) -> dict[str, dict]:
    """Every preset key as "table.key" (or "key"), with its schema."""
    definitions = schema["$defs"]
    leaves = {}
    for key, field in schema["properties"].items():
        references = [field] if "$ref" in field else field.get("oneOf", [])
        tables = [definitions[item["$ref"].split("/")[-1]] for item in references if "$ref" in item]
        if not tables:
            leaves[key] = field
        for table in tables:
            for name, sub in table["properties"].items():
                leaves[f"{key}.{name}"] = sub
    return leaves


def test_schema_describes_every_key():
    leaves = schema_leaves(preset_schema())
    assert "look.block_gap_px" in leaves and "fx.glow_radius_px" in leaves and "analysis.low_fft_size" in leaves
    assert sorted(key for key, field in leaves.items() if not field.get("description")) == []


def test_schema_writes_colors_as_hex_strings():
    schema = preset_schema()
    assert schema["properties"]["background"]["default"] == "#0000FF"
    assert schema["properties"]["background"]["format"] == "color"
    assert schema["$defs"]["Fill"]["properties"]["colors"]["items"]["format"] == "color"


@pytest.mark.parametrize("name", builtin_preset_names())
@pytest.mark.parametrize("full", [False, True])
def test_presets_written_as_toml_read_back_equal(name, full):
    preset = load_preset(name)
    assert parse_preset(preset_to_toml(preset, full=full)) == preset


def test_toml_lists_only_changed_keys_by_default():
    preset = override_preset(
        load_preset("default"),
        ['name=Mine "2"', "background=#00FF00", "fill.mode=height", 'fill.colors=["#00FF66", "#FFE000"]'],
    )
    text = preset_to_toml(preset)
    assert parse_preset(text) == preset
    assert 'name = "Mine \\"2\\""' in text
    assert 'background = "#00FF00"' in text and "foreground" not in text
    assert "[analysis]" not in text and "[look]" not in text
    assert 'colors = ["#00FF66", "#FFE000"]' in text


def test_toml_keeps_the_look_kind_when_it_is_not_flat():
    text = preset_to_toml(load_preset("unity-classic"))
    assert 'kind = "perspective"' in text and "max_frequency = inf" in text


def test_saved_user_presets_load_by_name(user_presets, capsys):
    from audio_spectrum import save_user_preset, user_preset_names
    preset = override_preset(load_preset("bars"), ["name=夜の青", "background=#00FF00"])
    path = save_user_preset(preset)
    assert path == user_presets / "夜の青.toml"
    assert "[look]" in path.read_text(encoding="utf-8") and "foreground" not in path.read_text(encoding="utf-8")
    assert user_preset_names() == ["夜の青"]
    assert load_preset("夜の青") == preset
    assert main(["presets", "list"]) == 0
    assert capsys.readouterr().out.split() == ["bars", "blocks", "default", "glow", "unity-classic", "夜の青"]


def test_saving_refuses_to_overwrite_unless_asked(user_presets):
    from audio_spectrum import OutputExistsError, save_user_preset
    first = override_preset(load_preset("default"), ["name=mine"])
    second = override_preset(first, ["look.max_height=0.4"])
    save_user_preset(first)
    with pytest.raises(OutputExistsError):
        save_user_preset(second)
    assert load_preset("mine") == first
    save_user_preset(second, overwrite=True)
    assert load_preset("mine") == second
    assert sorted(path.name for path in user_presets.iterdir()) == ["mine.toml"]


@pytest.mark.parametrize("name", ["default", "glow", "", " padded", "a/b", "a\\\\b", "a:b", ".hidden", "x.toml", "x" * 101])
def test_unusable_preset_names_are_refused(name, user_presets):
    from audio_spectrum import save_user_preset
    with pytest.raises(PresetError):
        save_user_preset(Preset(name=name))
    assert not user_presets.exists() or not list(user_presets.iterdir())


def test_built_in_names_are_reserved(user_presets, capsys):
    from audio_spectrum import shadowed_user_preset_names, user_preset_names
    user_presets.mkdir()
    (user_presets / "default.toml").write_text('name = "default"\nbackground = "#00FF00"\n', encoding="utf-8")
    assert user_preset_names() == [] and shadowed_user_preset_names() == ["default"]
    assert load_preset("default").background == (0, 0, 255)
    assert main(["presets", "list"]) == 0
    captured = capsys.readouterr()
    assert captured.out.split() == ["bars", "blocks", "default", "glow", "unity-classic"]
    assert "user preset 'default'" in captured.err and "reserved" in captured.err


def test_unknown_names_list_user_presets_too(user_presets):
    from audio_spectrum import save_user_preset
    save_user_preset(Preset(name="mine"))
    with pytest.raises(PresetError, match="user presets: mine"):
        load_preset("nothing")


def test_the_folder_comes_from_the_environment(user_presets, monkeypatch):
    from audio_spectrum import user_preset_folder
    assert user_preset_folder() == user_presets
    monkeypatch.delenv("AUDIO_SPECTRUM_PRESET_DIR")
    assert str(user_preset_folder()).endswith("Library/Application Support/audio-spectrum/presets")
