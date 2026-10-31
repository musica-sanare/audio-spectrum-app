"""The GUI server: local security rules and the API the page uses. Skipped without the gui extra."""

import subprocess
import sys

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
    assert api.get("/api/presets").json() == {"builtin": ["bars", "blocks", "default", "glow", "unity-classic"]}
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
