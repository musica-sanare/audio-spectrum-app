"""Still frames (`render_stills`, `still` command) and preset overrides (`override_preset`, `--set`)."""

import numpy as np
import pytest
import skia
import soundfile as sf

from audio_spectrum import PresetError, RenderJob, TimeRangeError, load_preset, override_preset, render_stills
from audio_spectrum.analysis import analyze
from audio_spectrum.audio import load_audio
from audio_spectrum.cli import main, seconds_label
from audio_spectrum.pipeline import _frames, still_frame_index
from signals import SAMPLE_RATE, sine

WIDTH, HEIGHT = 320, 180
FPS = 30


@pytest.fixture
def tone(tmp_path):
    path = tmp_path / "tone.wav"
    rising = sine(220, 2.0, 0.5) * np.linspace(0.1, 1.0, 2 * SAMPLE_RATE, dtype=np.float32)
    sf.write(path, rising + sine(3000, 2.0, 0.2), SAMPLE_RATE)
    return path


def read_png(path) -> np.ndarray:
    image = skia.Image.MakeFromEncoded(skia.Data.MakeWithCopy(path.read_bytes()))
    return image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3]


def test_stills_equal_the_video_frames_drawn_by_parallel_workers(tone):
    preset = load_preset("default")
    job = RenderJob(tone, tone.with_suffix(".mp4"), preset, width=WIDTH, height=HEIGHT, fps=FPS, workers=2)
    video_frames = list(_frames(job, analyze(load_audio(tone), FPS, preset.analysis)))
    stills = render_stills(tone, preset, [0.0, 0.5, 1.0 + 1 / 60, 1.99], WIDTH, HEIGHT, FPS)
    for still, index in zip(stills, [0, 15, 30, 59], strict=True):
        assert np.array_equal(still, video_frames[index])


def test_still_frame_index_is_the_frame_on_screen_at_that_time():
    assert still_frame_index(0.0, 30, 10.0) == 0
    assert still_frame_index(1 / 30 - 1e-6, 30, 10.0) == 0
    assert still_frame_index(2.3, 30, 10.0) == 69
    assert still_frame_index(61.5, 29.97, 100.0) == 1843


@pytest.mark.parametrize("seconds", [-0.1, 2.0, 5.0])
def test_stills_outside_the_audio_are_refused(tone, seconds):
    with pytest.raises(TimeRangeError, match="tone.wav"):
        render_stills(tone, load_preset("default"), [seconds], WIDTH, HEIGHT, FPS)


def test_still_command_writes_lossless_pngs_named_by_time(tone, tmp_path, capsys):
    out = tmp_path / "stills"
    code = main(["still", str(tone), "--at", "0.5", "--at", "1.25", "--out-dir", str(out), "--size", "320x180"])
    assert code == 0
    written = [out / "tone_0.5s.png", out / "tone_1.25s.png"]
    assert capsys.readouterr().out.split() == [str(path) for path in written]
    expected = render_stills(tone, load_preset("default"), [0.5, 1.25], WIDTH, HEIGHT, FPS)
    for path, frame in zip(written, expected, strict=True):
        assert np.array_equal(read_png(path), frame)
    assert sorted(path.name for path in out.iterdir()) == sorted(path.name for path in written)


def test_still_command_refuses_to_overwrite_and_reports_times_outside_the_audio(tone, tmp_path, capsys):
    args = ["still", str(tone), "--at", "1", "--out-dir", str(tmp_path), "--size", "320x180"]
    assert main(args) == 0
    before = (tmp_path / "tone_1s.png").read_bytes()
    assert main([*args, "--set", "look.max_height=0.5"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert (tmp_path / "tone_1s.png").read_bytes() == before
    assert main([*args, "--set", "look.max_height=0.5", "--overwrite"]) == 0
    assert (tmp_path / "tone_1s.png").read_bytes() != before
    assert main(["still", str(tone), "--at", "9", "--out-dir", str(tmp_path)]) == 1
    assert "outside the audio" in capsys.readouterr().err
    assert not (tmp_path / "tone_9s.png").exists()


def test_still_command_rejects_negative_times():
    with pytest.raises(SystemExit) as exc:
        main(["still", "song.wav", "--at", "-1"])
    assert exc.value.code == 2


def test_seconds_label_drops_trailing_zeros():
    assert [seconds_label(value) for value in (30.0, 61.5, 0.125, 2.3)] == ["30", "61.5", "0.125", "2.3"]


def test_overrides_change_only_the_given_keys():
    preset = load_preset("default")
    changed = override_preset(
        preset, ["analysis.min_frequency=40", "look.mirror=false", "analysis.channel=left", "background=#00FF00"]
    )
    assert changed == preset.model_copy(
        update={
            "analysis": preset.analysis.model_copy(update={"min_frequency": 40.0, "channel": "left"}),
            "look": preset.look.model_copy(update={"mirror": False}),
            "background": (0, 255, 0),
        }
    )


def test_no_overrides_or_unchanged_values_keep_the_preset():
    preset = load_preset("unity-classic")
    assert override_preset(preset, []) is preset
    assert override_preset(preset, ["look.depth=10.0", "analysis.max_frequency=inf"]) == preset


@pytest.mark.parametrize(
    ("assignment", "message"),
    [
        ("look.max_height", "KEY=VALUE"),
        ("look.max_height=2", "look.flat.max_height"),
        ("analysis.bandz=3", "analysis.bandz"),
        ("nothing.here=1", "'nothing' is not a preset table"),
        ("look.kind=perspective", "cannot change look.kind"),
    ],
)
def test_invalid_overrides_name_the_problem(assignment, message):
    with pytest.raises(PresetError, match=message):
        override_preset(load_preset("default"), [assignment])


def test_render_command_reports_invalid_overrides_as_usage_errors(tone, tmp_path, capsys):
    code = main(["render", str(tone), "--out-dir", str(tmp_path), "--set", "look.max_height=-1"])
    assert code == 2
    assert "look.flat.max_height" in capsys.readouterr().err
    assert not list(tmp_path.glob("*.mp4"))


def test_transparent_stills_are_rgba_pngs(tone, tmp_path, capsys):
    code = main(["still", str(tone), "--at", "1", "--out-dir", str(tmp_path), "--size", "320x180",
                 "--background", "transparent"])
    assert code == 0
    image = skia.Image.MakeFromEncoded(skia.Data.MakeWithCopy((tmp_path / "tone_1s.png").read_bytes()))
    decoded = image.toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
    expected = render_stills(tone, load_preset("default"), [1.0], WIDTH, HEIGHT, FPS, transparent=True)[0]
    assert np.array_equal(decoded, expected)
    assert decoded[0, 0, 3] == 0
