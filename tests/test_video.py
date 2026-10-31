"""End-to-end checks with ffmpeg: frame count, duration and audio/video sync."""

import json
import shutil
import subprocess
from fractions import Fraction

import numpy as np
import pytest
import soundfile as sf

from audio_spectrum.cli import main
from audio_spectrum.analysis import analyze, frame_count
from audio_spectrum.audio import load_audio
from audio_spectrum.encode import EncodeSettings, ffmpeg_fps
from audio_spectrum.pipeline import RenderJob, _frame_range, _frames, render_video
from audio_spectrum.presets import load_preset
from signals import SAMPLE_RATE, sine

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")

WIDTH, HEIGHT = 320, 180
CLICK_TIMES = [0.5, 1.5, 2.5]


@pytest.fixture
def click_track(tmp_path):
    """Three seconds of silence with a short 1 kHz burst at each of CLICK_TIMES."""
    signal = np.zeros(3 * SAMPLE_RATE, np.float32)
    burst = sine(1000, 0.05)
    for seconds in CLICK_TIMES:
        start = round(seconds * SAMPLE_RATE)
        signal[start:start + len(burst)] = burst
    path = tmp_path / "clicks.wav"
    sf.write(path, signal, SAMPLE_RATE)
    return path


def probe(path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(path)],
        capture_output=True, check=True,
    )
    return {stream["codec_type"]: stream for stream in json.loads(result.stdout)["streams"]}


def decoded_brightness(path) -> np.ndarray:
    """Mean brightness of each decoded frame."""
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(result.stdout, np.uint8).reshape(-1, HEIGHT * WIDTH).mean(axis=1)


@pytest.mark.parametrize("fps", [30.0, 60.0, 30000 / 1001])
def test_video_has_one_frame_per_frame_time_and_matches_the_audio_length(click_track, tmp_path, fps):
    output = tmp_path / "out.mp4"
    job = RenderJob(click_track, output, load_preset("default"), WIDTH, HEIGHT, fps, workers=1)
    frames = render_video(job).frames

    streams = probe(output)
    assert frames == frame_count(3 * SAMPLE_RATE, SAMPLE_RATE, fps)
    assert int(streams["video"]["nb_read_frames"]) == frames
    assert Fraction(streams["video"]["r_frame_rate"]) == Fraction(ffmpeg_fps(fps))
    assert float(streams["video"]["duration"]) == pytest.approx(3.0, abs=1 / fps)
    assert float(streams["audio"]["duration"]) == pytest.approx(3.0, abs=0.03)
    assert float(streams["video"]["start_time"]) == 0.0
    assert float(streams["audio"]["start_time"]) == 0.0
    assert set(streams) == {"video", "audio"}


def test_clicks_appear_on_the_frames_of_their_time(click_track, tmp_path):
    fps = 30
    output = tmp_path / "out.mp4"
    render_video(RenderJob(click_track, output, load_preset("default"), WIDTH, HEIGHT, fps, workers=1))

    brightness = decoded_brightness(output)
    quiet = np.median(brightness)
    for seconds in CLICK_TIMES:
        frame = round(seconds * fps)
        assert brightness[frame + 1] > quiet + 1, f"no response right after the click at {seconds} s"
        assert brightness[frame - 3] <= quiet + 0.2, f"response before the click at {seconds} s"
        # The brightest frame near each click is at most one frame away from the click time.
        nearby = brightness[frame - 5:frame + 6]
        assert abs(int(nearby.argmax()) - 5) <= 1


def test_parallel_rendering_produces_the_same_frames(click_track):
    preset = load_preset("default")
    values = analyze(load_audio(click_track), 30, preset.analysis)
    single = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, workers=1)
    parallel = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, workers=2)
    for one, other in zip(_frames(single, values), _frames(parallel, values), strict=True):
        assert np.array_equal(one, other)


def test_prores_output_without_audio(click_track, tmp_path):
    output = tmp_path / "out.mov"
    job = RenderJob(
        click_track, output, load_preset("default"), WIDTH, HEIGHT, 30,
        EncodeSettings(codec="prores", include_audio=False), workers=1,
    )
    render_video(job)
    streams = probe(output)
    assert streams["video"]["codec_name"] == "prores"
    assert "audio" not in streams


def test_cli_prores4444_keeps_full_color_resolution(click_track, tmp_path):
    output = tmp_path / "out.mov"
    args = ["render", str(click_track), "-o", str(output), "--size", f"{WIDTH}x{HEIGHT}", "--codec", "prores4444"]
    assert main([*args, "--workers", "1"]) == 0
    video = probe(output)["video"]
    assert video["codec_name"] == "prores"
    assert video["pix_fmt"].startswith("yuv444")


def test_cli_renders_green_back_next_to_the_input(click_track):
    assert main(["render", str(click_track), "--size", f"{WIDTH}x{HEIGHT}", "--background", "green", "--workers", "1"]) == 0
    output = click_track.with_name("clicks_spectrum.mp4")
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    )
    corner = np.frombuffer(result.stdout, np.uint8)[:3]
    assert corner[1] > 240 and corner[0] < 15 and corner[2] < 15


def decoded_rgba(path, frame: int) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(result.stdout, np.uint8).reshape(HEIGHT, WIDTH, 4)


def test_cli_transparent_background_keeps_alpha_in_prores4444(click_track, tmp_path):
    output = tmp_path / "out.mov"
    args = ["render", str(click_track), "-o", str(output), "--size", f"{WIDTH}x{HEIGHT}", "--codec", "prores4444",
            "--background", "transparent", "--workers", "2"]
    assert main(args) == 0
    streams = probe(output)
    assert streams["video"]["pix_fmt"].startswith("yuva444")
    assert int(streams["video"]["nb_read_frames"]) == frame_count(3 * SAMPLE_RATE, SAMPLE_RATE, 30)
    assert "audio" in streams
    frame = decoded_rgba(output, 15)  # the click at 0.5 s
    alpha = frame[:, :, 3]
    assert alpha[0, 0] == 0 and alpha[-1, -1] == 0
    assert np.any(alpha == 255)
    assert np.all(frame[alpha == 255][:, :3] >= 250)


def test_cli_refuses_a_transparent_background_without_prores4444(click_track, tmp_path):
    for codec in ("h264", "prores"):
        with pytest.raises(SystemExit) as exc:
            main(["render", str(click_track), "-o", str(tmp_path / "out.mov"), "--codec", codec,
                  "--background", "transparent"])
        assert exc.value.code == 2
    assert [path.name for path in tmp_path.iterdir()] == ["clicks.wav"]


def test_parallel_rendering_produces_the_same_transparent_frames(click_track):
    preset = load_preset("default")
    values = analyze(load_audio(click_track), 30, preset.analysis)
    alpha = EncodeSettings(codec="prores", prores_profile=4, alpha=True)
    single = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, alpha, workers=1)
    parallel = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, alpha, workers=2)
    for one, other in zip(_frames(single, values), _frames(parallel, values), strict=True):
        assert one.shape == (HEIGHT, WIDTH, 4)
        assert np.array_equal(one, other)


@pytest.mark.parametrize(("codec", "profile"), [("h264", 2), ("prores", 2), ("prores", 3)])
def test_alpha_needs_prores4444(codec, profile):
    with pytest.raises(ValueError, match="ProRes 4444"):
        EncodeSettings(codec=codec, prores_profile=profile, alpha=True)


def decoded_audio(path) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE),
         "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(result.stdout, np.float32)


def test_a_part_of_the_song_keeps_frames_and_audio_in_sync(click_track, tmp_path):
    output = tmp_path / "part.mov"
    job = RenderJob(
        click_track, output, load_preset("default"), WIDTH, HEIGHT, 30,
        EncodeSettings(codec="prores", prores_profile=4), workers=1, start=1.0, duration=1.0,
    )
    result = render_video(job)
    assert result.frames == 30
    streams = probe(output)
    assert int(streams["video"]["nb_read_frames"]) == 30
    assert abs(float(streams["audio"]["duration"]) - 1.0) < 1 / 30
    # The click at 1.5 s of the song is at 0.5 s of the part, in the audio and on frame 15 of the video.
    audio = decoded_audio(output)
    onset = int(np.argmax(np.abs(audio) > 0.1))
    assert abs(onset / SAMPLE_RATE - 0.5) < 0.001
    brightness = decoded_brightness(output)
    assert abs(int(brightness[10:20].argmax()) + 10 - 15) <= 1


def test_part_frames_equal_the_full_video_frames(click_track):
    preset = load_preset("default")
    values = analyze(load_audio(click_track), 30, preset.analysis)
    full = list(_frames(RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, workers=1), values))
    job = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, workers=1, start=1.01, duration=0.5)
    first, last = _frame_range(job, 3.0, len(values))
    assert (first, last) == (30, 45)
    part = list(_frames(job, values[first:last]))
    assert all(np.array_equal(one, other) for one, other in zip(part, full[30:45], strict=True))


def test_a_part_starting_at_zero_trims_the_audio_too(click_track, tmp_path):
    output = tmp_path / "head.mp4"
    assert main(["render", str(click_track), "-o", str(output), "--size", f"{WIDTH}x{HEIGHT}", "--workers", "1",
                 "--duration", "1"]) == 0
    streams = probe(output)
    assert int(streams["video"]["nb_read_frames"]) == 30
    assert abs(float(streams["audio"]["duration"]) - 1.0) < 0.05


def test_a_part_starting_after_the_end_fails_for_that_file(click_track, tmp_path, capsys):
    code = main(["render", str(click_track), "-o", str(tmp_path / "late.mp4"), "--start", "5", "--progress", "json"])
    assert code == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[0]["code"] == "time_out_of_range"
    assert not (tmp_path / "late.mp4").exists()


@pytest.mark.parametrize("args", [["--start", "-1"], ["--duration", "0"], ["--duration", "nan"]])
def test_invalid_ranges_are_usage_errors(click_track, args):
    with pytest.raises(SystemExit) as exc:
        main(["render", str(click_track), *args])
    assert exc.value.code == 2
