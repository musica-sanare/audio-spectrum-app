"""End-to-end checks with ffmpeg: frame count, duration and audio/video sync."""

import json
import shutil
import subprocess
from fractions import Fraction

import numpy as np
import pytest
import soundfile as sf

from audio_spectrum.__main__ import main
from audio_spectrum.analysis import analyze, frame_count
from audio_spectrum.audio import load_audio
from audio_spectrum.encode import EncodeSettings, ffmpeg_fps
from audio_spectrum.pipeline import RenderJob, _frames, render_video
from audio_spectrum.presets import PRESETS
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
    job = RenderJob(click_track, output, PRESETS["default"], WIDTH, HEIGHT, fps, workers=1)
    frames = render_video(job)

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
    render_video(RenderJob(click_track, output, PRESETS["default"], WIDTH, HEIGHT, fps, workers=1))

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
    preset = PRESETS["default"]
    values = analyze(load_audio(click_track), 30, preset.analysis)
    single = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, workers=1)
    parallel = RenderJob(click_track, click_track, preset, WIDTH, HEIGHT, 30, workers=2)
    for one, other in zip(_frames(single, values), _frames(parallel, values), strict=True):
        assert np.array_equal(one, other)


def test_prores_output_without_audio(click_track, tmp_path):
    output = tmp_path / "out.mov"
    job = RenderJob(
        click_track, output, PRESETS["default"], WIDTH, HEIGHT, 30,
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
