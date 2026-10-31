English | [日本語](../ja/EMBEDDING.md) | [Español](../es/EMBEDDING.md) · [Docs index](README.md)

# Embedding guide

How scripts and apps that embed audio-spectrum-app talk to it. The CLI and the Python API are the stable interface:
tools in any language can run the CLI and read its JSON progress events, and Python apps can call the API directly.
For everyday use and the full command reference, see the [user guide](USER_GUIDE.md).

## 1. JSON progress events

With `--progress json`, the CLI prints one JSON object per line on stdout. Error text still goes to stderr. Exit codes
are listed in the [user guide](USER_GUIDE.md#exit-codes).

| `event` | Fields | When |
|---|---|---|
| `start` | `input`, `output`, `frames`, `index`, `count` | A file starts rendering (`index` counts from 1) |
| `progress` | `input`, `frame`, `frames` | During rendering, at most about four times a second, and at the last frame |
| `done` | `input`, `output`, `seconds` | A file finished |
| `error` | `input` (absent for errors before any file), `code`, `message` | A file failed, or the run could not start |
| `finished` | `succeeded`, `failed` | All files were processed |
| `interrupted` | | The run was interrupted |

Error codes:

- `decode_failed`, `encode_failed`, `output_exists`, `worker_failed`, `preset_invalid`, `ffmpeg_not_found`
- `time_out_of_range`: `--start` beyond the end of a song
- `backdrop_failed`: API only ([Backdrops](#backdrops))

```json
{"event": "start", "input": "a.wav", "output": "a_spectrum.mp4", "frames": 7644, "index": 1, "count": 2}
{"event": "progress", "input": "a.wav", "frame": 3000, "frames": 7644}
{"event": "done", "input": "a.wav", "output": "a_spectrum.mp4", "seconds": 114.2}
{"event": "error", "input": "b.wav", "code": "decode_failed", "message": "b.wav: cannot decode audio (...)"}
{"event": "finished", "succeeded": 1, "failed": 1}
```

## 2. Python API

The names exported by the `audio_spectrum` package are the public API; everything else may change.

> [!WARNING]
> Call the API under `if __name__ == "__main__":`. Frames are drawn in several processes, which re-import the calling
> script. Without the guard the render fails with a `WorkerError` that says so. Passing `workers=1` avoids extra
> processes.

### Rendering a video

```python
from pathlib import Path

from audio_spectrum import RenderJob, load_preset, render_video


def main() -> None:
    job = RenderJob(
        audio_path=Path("song.wav"),
        output_path=Path("song_spectrum.mp4"),
        preset=load_preset("default"),   # or a path to a .toml file
        width=1920, height=1080, fps=30,
    )
    result = render_video(job, progress=lambda done, total: None, cancel=lambda: False)
    print(result.output_path, result.frames, result.seconds)


if __name__ == "__main__":  # required, see above
    main()
```

- On failure, `render_video` raises a subclass of `AudioSpectrumError`: `PresetError`, `DecodeError`,
  `EncodeError`, `OutputExistsError`, `WorkerError`, `FfmpegNotFoundError`, `BackdropError`, or `Cancelled` when
  `cancel` returns true. No output file is left behind in any of these cases.
- `RenderJob(..., start=10.0, duration=5.0)` renders part of a song, like `--start` and `--duration`. The frames
  are identical to those of the full video, and the audio is cut at the same time.
- A transparent background is an output setting: `EncodeSettings(codec="prores", prores_profile=4, alpha=True)` in
  `RenderJob.encode`. Other codecs with `alpha=True` raise `ValueError`.

### Stills and previews

- `render_stills(audio_path, preset, times, width, height, fps)` returns the frames shown at the given times (in
  seconds), without writing files.
  - The frames are `(height, width, 3)` `uint8` RGB arrays. With `transparent=True` they are `(height, width, 4)`
    RGBA arrays with straight alpha.
  - It raises `TimeRangeError` (code `time_out_of_range`) for a time outside the audio, and the same decoding errors
    as `render_video`.
  - It draws in the calling process.
- `Preview(audio_path, fps)` decodes a song once.
  - `preview.frames(preset, times, width, height)` then returns frames like `render_stills`.
  - It keeps the analysis for the last few analysis settings. A change of the look alone renders a 1080p frame in
    about 20 ms.
  - `preview.duration` is the song's length.
  - It is not thread-safe.
- `encode_png(frame)` returns a frame (RGB, or RGBA with alpha) as lossless PNG bytes.

### Presets

- `override_preset(preset, ["look.max_height=0.4"])` applies overrides like `--set` and returns a new preset. It
  raises `PresetError` for an invalid result.
- `preset_to_toml(preset)` returns the preset as TOML with only the keys that differ from `default`
  (`full=True` writes every key). `load_preset` reads it back to an equal preset.
- `save_user_preset(preset, overwrite=False)` writes a preset into the user folder and returns its path.
  - `user_preset_names()`, `shadowed_user_preset_names()` and `user_preset_folder()` describe the folder.
  - `load_preset(name)` finds user presets by name after the built-in ones.
- `preset_schema()` returns the JSON schema of a preset: types, ranges, defaults and a description of every key,
  with colors as `"#RRGGBB"` strings.
- `preset_warnings(preset)` returns the warnings of `presets check` as a list.

### Backdrops

`RenderJob(..., backdrop=...)` draws the spectrum over pictures that your app supplies, instead of the preset's
background color. An example is a background image with lyrics captions.

- The backdrop is any object with a method `frame(index, seconds, width, height)` that returns a
  `(height, width, 3)` `uint8` RGB array.
- `index` is the frame of the whole song and `seconds` its time (`index / fps`), also when only part of the song is
  rendered.
- It is sent to every worker process, so it must be picklable. Keep paths and settings in it and load pictures
  lazily.
- `render_stills` and `Preview.frames` take the same `backdrop`.
- A backdrop that raises, or returns a picture of the wrong size, stops the render with a `BackdropError` (code
  `backdrop_failed`) and leaves no file.
- It cannot be combined with a transparent background.

Example:

```python
import numpy as np
import skia


class StillImage:
    """One image file under the whole video, loaded once per worker process."""

    def __init__(self, path):
        self.path = str(path)
        self._picture = None

    def frame(self, index, seconds, width, height) -> np.ndarray:
        if self._picture is None:
            image = skia.Image.open(self.path).resize(width, height)
            self._picture = image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3].copy()
        return self._picture


job = RenderJob(..., backdrop=StillImage("background.png"))
```
