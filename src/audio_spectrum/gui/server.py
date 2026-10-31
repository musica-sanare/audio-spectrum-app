"""Start the GUI: a local server on 127.0.0.1 with a per-session token, and the page in the default browser."""

import secrets
import socket
import sys
import threading
import webbrowser

import uvicorn

from audio_spectrum.gui.app import create_app

HOST = "127.0.0.1"


def run(port: int = 0, open_browser: bool = True) -> None:
    """Serve until Ctrl+C. Port 0 picks a free port."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST, port))
    port = listener.getsockname()[1]
    token = secrets.token_urlsafe(24)
    app = create_app(token, {f"{HOST}:{port}", f"localhost:{port}"})
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    url = f"http://{HOST}:{port}/?token={token}"
    print(f"audio-spectrum GUI at {url}\nPress Ctrl+C to stop.", file=sys.stderr, flush=True)
    if open_browser:
        threading.Thread(target=_open_when_started, args=(server, url), daemon=True).start()
    server.run(sockets=[listener])


def _open_when_started(server: uvicorn.Server, url: str) -> None:
    for _ in range(100):
        if server.started:
            webbrowser.open(url)
            return
        threading.Event().wait(0.05)
