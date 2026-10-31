"""The GUI's HTTP API and page. Every request must come to an expected host, and API requests must carry the session
token, so other web pages in the browser cannot drive the server (see the Phase 3 plan, "Local security")."""

import dataclasses
import hmac
import shutil
import subprocess
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from audio_spectrum import (
    AudioSpectrumError,
    Cancelled,
    EncodeSettings,
    FfmpegNotFoundError,
    Preset,
    Preview,
    RenderJob,
    builtin_preset_names,
    encode_png,
    load_preset,
    preset_schema,
    preset_warnings,
    render_video,
    save_user_preset,
    shadowed_user_preset_names,
    user_preset_names,
)
from audio_spectrum.gui.dialogs import DialogUnavailable, Dialogs, MacDialogs

TOKEN_HEADER = "x-token"
MAX_SIZE = 7680
STATIC = Path(__file__).parent / "static"
CLIP_SECONDS = 5.0
# Clips are only for looking at motion in the page: fast settings, played by any browser.
CLIP_ENCODING = EncodeSettings(codec="h264", crf=20, x264_preset="veryfast")
FORMATS = {
    "h264": (EncodeSettings(), ".mp4"),
    "prores": (EncodeSettings(codec="prores"), ".mov"),
    "prores4444": (EncodeSettings(codec="prores", prores_profile=4), ".mov"),
}
SHUTDOWN_WAIT_SECONDS = 30


class PromptRequest(BaseModel):
    prompt: str = ""


class SongRequest(BaseModel):
    path: str
    fps: float = Field(30.0, gt=0.0, le=240.0)


class StillRequest(BaseModel):
    preset: dict
    time: float
    width: int = Field(1920, ge=16, le=MAX_SIZE)
    height: int = Field(1080, ge=16, le=MAX_SIZE)
    transparent: bool = False


class ClipRequest(BaseModel):
    preset: dict
    start: float = Field(ge=0.0)
    width: int = Field(1920, ge=16, le=MAX_SIZE)
    height: int = Field(1080, ge=16, le=MAX_SIZE)


class SaveRequest(BaseModel):
    preset: dict
    overwrite: bool = False


class RenderRequest(BaseModel):
    preset: dict
    output_dir: str | None = None
    """Folder for the video; None means next to the song, as with the CLI."""
    width: int = Field(1920, ge=16, le=MAX_SIZE)
    height: int = Field(1080, ge=16, le=MAX_SIZE)
    fps: float = Field(30.0, gt=0.0, le=240.0)
    format: Literal["h264", "prores", "prores4444"] = "h264"
    transparent: bool = False
    overwrite: bool = False


class RenderTask:
    """The one render the page can run at a time, in a background thread. The page polls `snapshot`."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.thread: threading.Thread | None = None
        self.state = "idle"
        self.frame = 0
        self.frames = 0
        self.output: Path | None = None
        self.seconds: float | None = None
        self.error: dict | None = None

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, job: RenderJob) -> None:
        self.cancel.clear()
        self.state, self.frame, self.frames, self.output, self.seconds, self.error = (
            "running", 0, 0, job.output_path, None, None,
        )
        self.thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        self.thread.start()

    def _run(self, job: RenderJob) -> None:
        started = time.perf_counter()
        try:
            render_video(job, progress=self._progress, cancel=self.cancel.is_set)
        except Cancelled:
            state, error = "cancelled", None
        except AudioSpectrumError as failure:
            state, error = "failed", {"code": failure.code, "message": str(failure)}
        else:
            state, error = "done", None
        with self.lock:
            self.state, self.error, self.seconds = state, error, time.perf_counter() - started

    def _progress(self, done: int, total: int) -> None:
        with self.lock:
            self.frame, self.frames = done, total

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "state": self.state, "frame": self.frame, "frames": self.frames,
                "output": str(self.output) if self.output else None, "seconds": self.seconds, "error": self.error,
            }

    def stop(self) -> None:
        """Cancel a running render and wait for it, so no temporary file is left when the server stops."""
        self.cancel.set()
        if self.thread is not None:
            self.thread.join(SHUTDOWN_WAIT_SECONDS)


class Session:
    """What the page is working on: the open song. FastAPI runs plain handlers in a thread pool, hence the locks."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.preview: Preview | None = None
        self.clip_lock = threading.Lock()
        self.render = RenderTask()


def create_app(token: str, allowed_hosts: set[str], dialogs: Dialogs | None = None) -> FastAPI:
    session = Session()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        session.render.stop()

    app = FastAPI(title="audio-spectrum", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    dialogs = dialogs or MacDialogs()

    @app.middleware("http")
    async def guard(request: Request, call_next):
        # A foreign Host header means DNS rebinding; a missing token means another page in the browser.
        if request.headers.get("host") not in allowed_hosts:
            return _error(403, "forbidden", "unexpected host")
        if request.url.path.startswith("/api/") and not hmac.compare_digest(
            request.headers.get(TOKEN_HEADER, ""), token
        ):
            return _error(403, "forbidden", "missing or wrong session token")
        return await call_next(request)

    @app.exception_handler(AudioSpectrumError)
    async def core_error(request: Request, error: AudioSpectrumError):
        status = 500 if isinstance(error, FfmpegNotFoundError) else 400
        return _error(status, error.code, str(error))

    @app.exception_handler(DialogUnavailable)
    async def no_dialog(request: Request, error: DialogUnavailable):
        return _error(501, "dialog_unavailable", str(error))

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return (STATIC / "index.html").read_text(encoding="utf-8")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/api/presets")
    def presets() -> dict:
        return {"builtin": builtin_preset_names(), "user": user_preset_names(), "shadowed": shadowed_user_preset_names()}

    @app.get("/api/presets/{name}")
    def preset(name: str) -> Response:
        if name not in builtin_preset_names() + user_preset_names():
            return _error(404, "preset_not_found", f"unknown preset {name!r}")
        return Response(load_preset(name).model_dump_json(), media_type="application/json")

    @app.post("/api/presets")
    def save_preset(request: SaveRequest) -> Response:
        checked = _validate(request.preset)
        if isinstance(checked, Response):
            return checked
        path = save_user_preset(checked, overwrite=request.overwrite)
        return JSONResponse({"name": checked.name, "path": str(path)})

    @app.get("/api/schema")
    def schema() -> dict:
        return preset_schema()

    @app.post("/api/warnings")
    def warnings(data: dict) -> Response:
        checked = _validate(data)
        if isinstance(checked, Response):
            return checked
        return JSONResponse({"warnings": preset_warnings(checked)})

    @app.post("/api/dialogs/audio")
    def choose_audio(request: PromptRequest) -> dict:
        return {"path": dialogs.choose_file(request.prompt)}

    @app.post("/api/dialogs/folder")
    def choose_folder(request: PromptRequest) -> dict:
        return {"path": dialogs.choose_folder(request.prompt)}

    @app.post("/api/song")
    def open_song(request: SongRequest) -> dict:
        path = Path(request.path).expanduser()
        preview = Preview(path, request.fps)
        with session.lock:
            session.preview = preview
        return {"path": str(path), "name": path.name, "duration": preview.duration, "fps": request.fps}

    @app.post("/api/still")
    def still(request: StillRequest) -> Response:
        checked = _validate(request.preset)
        if isinstance(checked, Response):
            return checked
        with session.lock:
            if session.preview is None:
                return _error(409, "no_song", "open a song first")
            frame = session.preview.frames(
                checked, [request.time], request.width, request.height, request.transparent
            )[0]
        return Response(encode_png(frame), media_type="image/png")

    @app.post("/api/clip")
    def clip(request: ClipRequest) -> Response:
        """A short H.264 video with sound from `start`, rendered like the final output, to preview motion."""
        checked = _validate(request.preset)
        if isinstance(checked, Response):
            return checked
        with session.lock:
            preview = session.preview
        if preview is None:
            return _error(409, "no_song", "open a song first")
        if not session.clip_lock.acquire(blocking=False):
            return _error(409, "busy", "a clip is already being rendered")
        try:
            with tempfile.TemporaryDirectory(prefix="audio-spectrum-clip-") as folder:
                output = Path(folder) / "clip.mp4"
                # One process: for 150 frames, starting worker processes costs more than it saves (4.6 s against
                # 5.1 s for a 1080p clip, and about 15 s the first time while the workers load their libraries).
                job = RenderJob(
                    preview.audio_path, output, checked, request.width, request.height, preview.fps, CLIP_ENCODING,
                    workers=1, start=min(request.start, max(preview.duration - CLIP_SECONDS, 0.0)),
                    duration=CLIP_SECONDS,
                )
                render_video(job)
                return Response(output.read_bytes(), media_type="video/mp4")
        finally:
            session.clip_lock.release()

    @app.post("/api/render")
    def start_render(request: RenderRequest) -> Response:
        checked = _validate(request.preset)
        if isinstance(checked, Response):
            return checked
        with session.lock:
            preview = session.preview
        if preview is None:
            return _error(409, "no_song", "open a song first")
        if request.transparent and request.format != "prores4444":
            return _error(400, "usage", "a transparent background needs ProRes 4444")
        encode, suffix = FORMATS[request.format]
        encode = dataclasses.replace(encode, alpha=request.transparent)
        folder = Path(request.output_dir).expanduser() if request.output_dir else preview.audio_path.parent
        output = folder / f"{preview.audio_path.stem}_spectrum{suffix}"
        with session.render.lock:
            if session.render.running():
                return _error(409, "busy", "a render is already running")
        if output.exists() and not request.overwrite:
            message = f"{output} already exists"
            return JSONResponse({"code": "output_exists", "message": message, "output": str(output)}, status_code=409)
        folder.mkdir(parents=True, exist_ok=True)
        job = RenderJob(
            preview.audio_path, output, checked, request.width, request.height, request.fps, encode,
            overwrite=request.overwrite,
        )
        session.render.start(job)
        return JSONResponse(session.render.snapshot())

    @app.get("/api/render")
    def render_status() -> dict:
        return session.render.snapshot()

    @app.post("/api/render/cancel")
    def cancel_render() -> dict:
        session.render.cancel.set()
        return session.render.snapshot()

    @app.post("/api/reveal")
    def reveal() -> Response:
        """Show the last rendered video in the Finder. Only that file: the page cannot name other paths."""
        status = session.render.snapshot()
        output = Path(status["output"]) if status["output"] and status["state"] == "done" else None
        opener = shutil.which("open")
        if output is None or not output.exists():
            return _error(404, "no_output", "no finished video to show")
        if opener is None:
            return _error(501, "dialog_unavailable", "showing files needs macOS")
        subprocess.run([opener, "-R", str(output)], check=False)
        return JSONResponse({"path": str(output)})

    return app


def _validate(data: dict) -> Preset | Response:
    try:
        return Preset.model_validate(data)
    except ValidationError as error:
        problems = [
            {"key": ".".join(str(part) for part in problem["loc"]), "message": problem["msg"]}
            for problem in error.errors()
        ]
        return JSONResponse({"code": "preset_invalid", "errors": problems}, status_code=422)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status)
