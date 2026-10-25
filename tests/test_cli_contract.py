"""The CLI and Python API contract for embedding apps: events, exit codes, safe output and cancellation."""

import json
import os
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
import pytest
import soundfile as sf

import audio_spectrum
from audio_spectrum import (
    Cancelled,
    EncodeError,
    EncodeSettings,
    OutputExistsError,
    RenderJob,
    load_preset,
    render_video,
)
from audio_spectrum.cli import main
from signals import SAMPLE_RATE, sine

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")

SMALL = ["--size", "320x180", "--workers", "1"]


def write_tone(path, seconds=1.0):
    sf.write(path, sine(440, seconds, amplitude=0.5), SAMPLE_RATE)
    return path


def json_events(capsys) -> list[dict]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def leftovers(folder) -> list[str]:
    return sorted(path.name for path in folder.iterdir() if ".partial-" in path.name)


def test_json_events_for_a_batch_with_one_failure(tmp_path, capsys):
    good = write_tone(tmp_path / "good.wav")
    bad = tmp_path / "bad.wav"
    bad.write_text("not audio")
    later = write_tone(tmp_path / "later.wav")
    out = tmp_path / "out"

    code = main(["render", str(good), str(bad), str(later), "--out-dir", str(out), "--progress", "json", *SMALL])

    events = json_events(capsys)
    assert code == 1
    kinds = [event["event"] for event in events]
    assert kinds[0] == "start" and kinds[-1] == "finished"
    assert kinds.count("start") == 2 and kinds.count("done") == 2 and kinds.count("error") == 1
    start = events[0]
    assert start == {
        "event": "start", "input": str(good), "output": str(out / "good_spectrum.mp4"),
        "frames": 30, "index": 1, "count": 3,
    }
    error = next(event for event in events if event["event"] == "error")
    assert error["input"] == str(bad) and error["code"] == "decode_failed"
    progress = [event for event in events if event["event"] == "progress"]
    assert progress and all(event["frames"] == 30 for event in progress)
    assert events[-1] == {"event": "finished", "succeeded": 2, "failed": 1}
    assert sorted(path.name for path in out.iterdir()) == ["good_spectrum.mp4", "later_spectrum.mp4"]


def test_fail_fast_stops_at_the_first_failure(tmp_path, capsys):
    bad = tmp_path / "bad.wav"
    bad.write_text("not audio")
    good = write_tone(tmp_path / "good.wav")
    code = main(["render", str(bad), str(good), "--fail-fast", "--progress", "json", *SMALL])
    assert code == 1
    assert json_events(capsys)[-1] == {"event": "finished", "succeeded": 0, "failed": 1}
    assert not (tmp_path / "good_spectrum.mp4").exists()


def test_existing_output_is_kept_unless_overwrite_is_given(tmp_path, capsys):
    audio = write_tone(tmp_path / "song.wav")
    output = tmp_path / "song_spectrum.mp4"
    output.write_bytes(b"keep me")

    assert main(["render", str(audio), "--progress", "json", *SMALL]) == 1
    assert json_events(capsys)[0]["code"] == "output_exists"
    assert output.read_bytes() == b"keep me"

    assert main(["render", str(audio), "--overwrite", "--progress", "none", *SMALL]) == 0
    assert output.stat().st_size > len(b"keep me")


def test_encoder_failure_leaves_no_files(tmp_path):
    audio = write_tone(tmp_path / "song.wav")
    output = tmp_path / "song.mp4"
    job = RenderJob(audio, output, load_preset("default"), 320, 180, encode=EncodeSettings(x264_preset="bogus"), workers=1)
    with pytest.raises(EncodeError, match="ffmpeg failed"):
        render_video(job)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["song.wav"]


def test_crf_outside_the_x264_range_is_a_usage_error():
    with pytest.raises(SystemExit) as exit_info:
        main(["render", "a.wav", "--crf", "99"])
    assert exit_info.value.code == 2


def test_missing_ffmpeg_exits_with_3(tmp_path, monkeypatch, capsys):
    audio = write_tone(tmp_path / "song.wav")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert main(["render", str(audio), "--progress", "json", *SMALL]) == 3
    assert json_events(capsys)[0]["code"] == "ffmpeg_not_found"


@pytest.mark.parametrize(
    "arguments",
    [
        ["a.wav", "b.wav", "-o", "x.mp4"],
        ["a.wav", "-o", "x.mp4", "--out-dir", "out"],
        ["one/a.wav", "two/a.wav", "--out-dir", "out"],
        ["a.wav", "--progress", "xml"],
    ],
)
def test_usage_errors_exit_with_2(arguments):
    with pytest.raises(SystemExit) as exit_info:
        main(["render", *arguments])
    assert exit_info.value.code == 2


def test_api_cancel_stops_and_removes_the_partial_file(tmp_path):
    audio = write_tone(tmp_path / "song.wav", seconds=2.0)
    output = tmp_path / "song.mp4"
    frames_seen = []

    def progress(done, total):
        frames_seen.append(done)

    job = RenderJob(audio, output, load_preset("default"), 320, 180, workers=2)
    with pytest.raises(Cancelled):
        render_video(job, progress, cancel=lambda: len(frames_seen) > 10)
    assert not output.exists()
    assert leftovers(tmp_path) == []


def test_api_refuses_to_overwrite_by_default(tmp_path):
    audio = write_tone(tmp_path / "song.wav")
    output = tmp_path / "song.mp4"
    output.write_bytes(b"keep me")
    with pytest.raises(OutputExistsError):
        render_video(RenderJob(audio, output, load_preset("default"), 320, 180, workers=1))
    result = render_video(RenderJob(audio, output, load_preset("default"), 320, 180, workers=1, overwrite=True))
    assert result.output_path == output and result.frames == 30


def test_public_api_names_are_importable():
    for name in audio_spectrum.__all__:
        assert hasattr(audio_spectrum, name)


@pytest.mark.parametrize("signal_number", [signal.SIGINT, signal.SIGTERM])
def test_interrupting_the_cli_exits_130_and_leaves_no_files(tmp_path, signal_number):
    audio = write_tone(tmp_path / "long.wav", seconds=120.0)
    process = subprocess.Popen(
        [sys.executable, "-m", "audio_spectrum", "render", str(audio), "--size", "1280x720", "--workers", "2",
         "--progress", "json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    # Wait until frames are flowing into the partial file, then interrupt like Ctrl+C or a kill would.
    deadline = time.monotonic() + 30
    while not leftovers(tmp_path) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert leftovers(tmp_path), "the render never started"
    time.sleep(0.3)
    os.kill(process.pid, signal_number)
    stdout, stderr = process.communicate(timeout=30)

    assert process.returncode == 130, stderr
    assert json.loads(stdout.splitlines()[-1]) == {"event": "interrupted"}
    assert sorted(path.name for path in tmp_path.iterdir()) == ["long.wav"]
    assert "Traceback" not in stderr
