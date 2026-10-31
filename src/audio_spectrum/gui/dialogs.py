"""Native file dialogs, opened by the local server: a web page cannot read local paths or pick an output folder."""

import shutil
import subprocess
import sys
from typing import Protocol

USER_CANCELED = "-128"


class DialogUnavailable(Exception):
    """Native dialogs are not available on this system."""


class Dialogs(Protocol):
    def choose_file(self, prompt: str) -> str | None:
        """The chosen file's path, or None when the dialog was cancelled."""
        ...

    def choose_folder(self, prompt: str) -> str | None:
        """The chosen folder's path, or None when the dialog was cancelled."""
        ...


class MacDialogs:
    """Finder dialogs through AppleScript, shown in front of the browser."""

    def choose_file(self, prompt: str) -> str | None:
        return self._choose(f"choose file with prompt {_quote(prompt)}")

    def choose_folder(self, prompt: str) -> str | None:
        return self._choose(f"choose folder with prompt {_quote(prompt)}")

    def _choose(self, command: str) -> str | None:
        osascript = shutil.which("osascript")
        if sys.platform != "darwin" or osascript is None:
            raise DialogUnavailable("file dialogs need macOS; type the path instead")
        # Asking the frontmost application (the browser) puts the dialog in front of it.
        script = f"tell application (path to frontmost application as text) to POSIX path of ({command})"
        result = subprocess.run([osascript, "-e", script], capture_output=True, text=True)
        if result.returncode != 0:
            if USER_CANCELED in result.stderr:
                return None
            raise DialogUnavailable(f"the file dialog failed: {result.stderr.strip()}")
        return result.stdout.strip()


def _quote(text: str) -> str:
    """An AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
