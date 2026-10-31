"""The GUI server: local security rules and the API the page uses. Skipped without the gui extra."""

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest
import skia
import soundfile as sf

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from audio_spectrum import Preset, load_preset, preset_schema, render_stills  # noqa: E402
from audio_spectrum.cli import main  # noqa: E402
from audio_spectrum.gui.app import create_app  # noqa: E402
from audio_spectrum.gui.dialogs import DialogUnavailable, _quote  # noqa: E402
from signals import SAMPLE_RATE, sine  # noqa: E402

TOKEN = "secret-token"
HOST = "testserver"


class FakeDialogs:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.prompts = []

    def choose_file(self, prompt):
        return self._reply(prompt)

    def choose_folder(self, prompt):
        return self._reply(prompt)

    def _reply(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.answer


def client(dialogs=None, token=TOKEN) -> TestClient:
    app = create_app(TOKEN, {HOST}, dialogs or FakeDialogs())
    return TestClient(app, headers={"X-Token": token} if token else {})


@pytest.fixture
def tone(tmp_path):
    path = tmp_path / "tone.wav"
    sf.write(path, sine(220, 2.0, 0.5) + sine(3000, 2.0, 0.2), SAMPLE_RATE)
    return path


def test_api_requests_need_the_session_token():
    assert client(token=None).get("/api/presets").status_code == 403
    assert client(token="wrong").get("/api/presets").status_code == 403
    assert client().get("/api/presets").status_code == 200


def test_requests_to_a_foreign_host_are_refused():
    # DNS rebinding: a page on evil.example resolves its name to 127.0.0.1 and sends its own Host header.
    response = client().get("/api/presets", headers={"Host": "evil.example:8000"})
    assert response.status_code == 403
    assert client(token=None).get("/", headers={"Host": "evil.example:8000"}).status_code == 403


def test_the_page_loads_without_the_token_but_sends_no_cross_origin_headers():
    response = client(token=None).get("/")
    assert response.status_code == 200 and "<html" in response.text
    preflight = client().options(
        "/api/presets", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_presets_and_schema():
    api = client()
    assert api.get("/api/presets").json() == {
        "builtin": ["bars", "blocks", "default", "glow", "unity-classic"], "user": [], "shadowed": [],
    }
    classic = api.get("/api/presets/unity-classic").json()
    assert classic["analysis"]["max_frequency"] == "Infinity" and classic["background"] == "#0000FF"
    assert api.get("/api/presets/nothing").status_code == 404
    assert api.get("/api/schema").json() == preset_schema()


def test_presets_survive_the_round_trip_through_the_page():
    api = client()
    for name in api.get("/api/presets").json()["builtin"]:
        data = api.get(f"/api/presets/{name}").json()
        assert api.post("/api/warnings", json=data).status_code == 200
        assert Preset.model_validate(data) == load_preset(name)


def test_warnings_and_invalid_presets():
    api = client()
    pale = api.get("/api/presets/default").json() | {"foreground": "#8080FF"}
    assert "close to the background" in api.post("/api/warnings", json=pale).json()["warnings"][0]
    broken = api.get("/api/presets/default").json()
    broken["look"]["max_height"] = 5
    response = api.post("/api/warnings", json=broken)
    assert response.status_code == 422
    assert response.json()["errors"][0]["key"] == "look.flat.max_height"


def test_dialogs_return_the_path_or_null():
    dialogs = FakeDialogs(answer="/Music/song.wav")
    api = client(dialogs)
    assert api.post("/api/dialogs/audio", json={"prompt": "Choose"}).json() == {"path": "/Music/song.wav"}
    assert api.post("/api/dialogs/folder", json={"prompt": "Where"}).json() == {"path": "/Music/song.wav"}
    assert dialogs.prompts == ["Choose", "Where"]
    assert client(FakeDialogs(answer=None)).post("/api/dialogs/audio", json={}).json() == {"path": None}
    unavailable = client(FakeDialogs(error=DialogUnavailable("needs macOS"))).post("/api/dialogs/audio", json={})
    assert unavailable.status_code == 501 and unavailable.json()["code"] == "dialog_unavailable"


def test_applescript_strings_are_quoted():
    assert _quote('Say "hi" \\ there') == '"Say \\"hi\\" \\\\ there"'


def test_stills_equal_the_core_stills(tone):
    api = client()
    assert api.post("/api/still", json={"preset": {"name": "x"}, "time": 1.0}).status_code == 409
    song = api.post("/api/song", json={"path": str(tone)}).json()
    assert song["name"] == "tone.wav" and abs(song["duration"] - 2.0) < 1e-9
    preset = api.get("/api/presets/glow").json()
    response = api.post("/api/still", json={"preset": preset, "time": 1.0, "width": 320, "height": 180})
    assert response.headers["content-type"] == "image/png"
    image = skia.Image.MakeFromEncoded(skia.Data.MakeWithCopy(response.content))
    decoded = image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3]
    assert np.array_equal(decoded, render_stills(tone, load_preset("glow"), [1.0], 320, 180)[0])


def test_song_and_time_errors_carry_core_error_codes(tone, tmp_path):
    api = client()
    missing = api.post("/api/song", json={"path": str(tmp_path / "missing.wav")})
    assert missing.status_code == 400 and missing.json()["code"] == "decode_failed"
    api.post("/api/song", json={"path": str(tone)})
    late = api.post("/api/still", json={"preset": {"name": "x"}, "time": 9.0})
    assert late.status_code == 400 and late.json()["code"] == "time_out_of_range"


def test_the_core_and_cli_do_not_import_the_gui_packages():
    code = "import sys, audio_spectrum, audio_spectrum.cli; print(sorted({'fastapi', 'uvicorn'} & set(sys.modules)))"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"


def test_gui_command_explains_the_missing_extra(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "audio_spectrum.gui.server", None)
    assert main(["gui", "--no-browser"]) == 2
    assert "uv sync --extra gui" in capsys.readouterr().err


def test_gui_command_reports_a_busy_port(capsys):
    import socket
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        assert main(["gui", "--no-browser", "--port", str(port)]) == 2
    assert f"cannot listen on 127.0.0.1:{port}" in capsys.readouterr().err


STATIC = Path(__file__).parent.parent / "src" / "audio_spectrum" / "gui" / "static"
LANGUAGES = ("en", "ja", "es")


def messages(language: str) -> dict:
    return json.loads((STATIC / "i18n" / f"{language}.json").read_text(encoding="utf-8"))


def test_every_language_has_the_same_messages_and_every_preset_key():
    from test_presets import schema_leaves
    keys = set(schema_leaves(preset_schema())) - {"schema_version"}
    english = messages("en")
    for language in LANGUAGES:
        texts = messages(language)
        assert set(texts["messages"]) == set(english["messages"]), language
        assert set(texts["keys"]) == keys, language
        assert all(entry["label"] and entry["help"] for entry in texts["keys"].values()), language


def test_the_page_uses_only_messages_that_exist():
    page = (STATIC / "index.html").read_text(encoding="utf-8") + (STATIC / "app.js").read_text(encoding="utf-8")
    used = set(re.findall(r'data-i18n(?:-placeholder)?="([\w.]+)"', page))
    used |= set(re.findall(r'\bt\("([\w.]+)"', page))
    used |= {f"section.{name}" for name in re.findall(r'\["(\w+)", \[', page)}
    assert used, "no messages found in the page"
    assert used <= set(messages("en")["messages"])
    codes = {f"error.{code}" for code in ("preset_invalid", "decode_failed", "time_out_of_range", "no_song", "busy")}
    assert codes <= set(messages("en")["messages"])


def test_static_files_are_served_without_the_token():
    api = client(token=None)
    for path in ("/static/app.js", "/static/app.css", "/static/i18n/ja.json"):
        assert api.get(path).status_code == 200, path
    assert client(token=None).get("/static/app.js", headers={"Host": "evil.example"}).status_code == 403


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_clips_are_short_videos_with_sound(tone):
    api = client()
    preset = api.get("/api/presets/default").json()
    assert api.post("/api/clip", json={"preset": preset, "start": 0.0}).status_code == 409
    api.post("/api/song", json={"path": str(tone)})
    response = api.post("/api/clip", json={"preset": preset, "start": 1.5, "width": 320, "height": 180})
    assert response.status_code == 200 and response.headers["content-type"] == "video/mp4"
    path = tone.with_name("clip.mp4")
    path.write_bytes(response.content)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_entries", "stream=codec_type,nb_read_frames,duration",
         "-of", "json", str(path)],
        capture_output=True, check=True, text=True,
    )
    streams = {stream["codec_type"]: stream for stream in json.loads(probe.stdout)["streams"]}
    # The song is 2 s long, so a 5-second clip asked for at 1.5 s starts at 0 and covers the whole song.
    assert int(streams["video"]["nb_read_frames"]) == 60
    assert "audio" in streams


def test_presets_can_be_saved_and_listed(user_presets):
    api = client()
    preset = api.get("/api/presets/bars").json() | {"name": "mine"}
    saved = api.post("/api/presets", json={"preset": preset})
    assert saved.status_code == 200 and saved.json()["path"] == str(user_presets / "mine.toml")
    assert api.get("/api/presets").json()["user"] == ["mine"]
    assert api.get("/api/presets/mine").json()["analysis"]["bands"] == 64
    again = api.post("/api/presets", json={"preset": preset})
    assert again.status_code == 400 and again.json()["code"] == "output_exists"
    assert api.post("/api/presets", json={"preset": preset, "overwrite": True}).status_code == 200
    builtin_name = api.post("/api/presets", json={"preset": preset | {"name": "default"}})
    assert builtin_name.status_code == 400 and builtin_name.json()["code"] == "preset_invalid"


def wait_for_render(api, seconds=120) -> dict:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        status = api.get("/api/render").json()
        if status["state"] != "running":
            return status
        time.sleep(0.1)
    raise AssertionError("the render did not finish")


def render_body(api, **options) -> dict:
    return {"preset": api.get("/api/presets/default").json(), "width": 320, "height": 180} | options


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_renders_run_in_the_background_and_report_progress(tone, monkeypatch):
    calls = []
    monkeypatch.setattr("audio_spectrum.gui.app.subprocess.run", lambda command, **_: calls.append(command))
    api = client()
    assert api.post("/api/reveal", json={}).status_code == 404
    assert api.post("/api/render", json=render_body(api)).json()["code"] == "no_song"
    api.post("/api/song", json={"path": str(tone)})
    assert api.post("/api/render", json=render_body(api, format="h264", transparent=True)).status_code == 400
    started = api.post("/api/render", json=render_body(api))
    assert started.status_code == 200 and started.json()["state"] == "running"
    status = wait_for_render(api)
    output = tone.with_name("tone_spectrum.mp4")
    assert status["state"] == "done" and status["output"] == str(output) and status["frame"] == status["frames"] == 60
    assert output.exists()
    exists = api.post("/api/render", json=render_body(api))
    assert exists.status_code == 409 and exists.json()["output"] == str(output)
    assert api.post("/api/reveal", json={}).json() == {"path": str(output)}
    assert calls and calls[0][1:] == ["-R", str(output)]
    assert api.post("/api/render", json=render_body(api, overwrite=True, output_dir=str(tone.parent / "out")))
    assert wait_for_render(api)["state"] == "done"
    assert (tone.parent / "out" / "tone_spectrum.mp4").exists()


@pytest.fixture
def long_tone(tmp_path):
    path = tmp_path / "long.wav"
    sf.write(path, sine(220, 60.0, 0.5), SAMPLE_RATE)
    return path


def leftovers(folder) -> list[str]:
    return sorted(path.name for path in folder.iterdir() if path.suffix in (".mp4", ".mov"))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_a_render_can_be_cancelled_and_only_one_runs_at_a_time(long_tone):
    api = client()
    api.post("/api/song", json={"path": str(long_tone)})
    body = render_body(api, width=1280, height=720)
    assert api.post("/api/render", json=body).status_code == 200
    busy = api.post("/api/render", json=body)
    assert busy.status_code == 409 and busy.json()["code"] == "busy"
    api.post("/api/render/cancel", json={})
    assert wait_for_render(api)["state"] == "cancelled"
    assert leftovers(long_tone.parent) == []


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_stopping_the_server_cancels_a_running_render(long_tone):
    with TestClient(create_app(TOKEN, {HOST}, FakeDialogs()), headers={"X-Token": TOKEN}) as api:
        api.post("/api/song", json={"path": str(long_tone)})
        assert api.post("/api/render", json=render_body(api, width=1280, height=720)).status_code == 200
    assert leftovers(long_tone.parent) == []
