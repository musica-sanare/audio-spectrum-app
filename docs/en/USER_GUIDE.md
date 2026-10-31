English | [日本語](../ja/USER_GUIDE.md) · [Docs index](README.md)

# User guide

audio-spectrum-app turns an audio file into a spectrum video on a solid blue or green background, ready to be keyed
over a background video in an editor such as iMovie. Everything runs offline on your Mac.

## 1. Setup

You need macOS (tested on an Apple Silicon M1), [Homebrew](https://brew.sh), `uv` and ffmpeg.

```bash
brew install uv ffmpeg
git clone <repository URL> audio-spectrum-app
cd audio-spectrum-app
uv sync
uv run audio-spectrum --version
```

`uv sync` installs Python 3.13 and the libraries into `.venv/` inside the folder. Nothing else on the system changes.

## 2. Everyday use

Render one song with the default look (1080p, 30 fps, white lines on blue, H.264):

```bash
uv run audio-spectrum render song.wav
```

The video is written next to the input as `song_spectrum.mp4`, with the song's audio included. Its length matches the
audio exactly, so it lines up with the background video when both start at zero.

More examples:

```bash
uv run audio-spectrum render song.wav --background green           # green back
uv run audio-spectrum render song.wav --size 2160p --fps 60        # 4K at 60 fps
uv run audio-spectrum render song.wav --codec prores4444           # cleanest keying, large .mov
uv run audio-spectrum render song.wav --codec prores4444 --background transparent   # no key color at all
uv run audio-spectrum render *.wav --out-dir ~/Movies/spectrum     # several songs at once
uv run audio-spectrum render song.wav --preset my-look.toml        # your own preset
```

### Trying a look quickly

Render single frames as PNG images instead of a whole video, and change preset keys on the command line with
`--set`:

```bash
uv run audio-spectrum still song.wav --at 30 --at 61.5                    # song_30s.png, song_61.5s.png
uv run audio-spectrum still song.wav --at 30 --set look.max_height=0.4 --overwrite
uv run audio-spectrum render song.wav --set analysis.min_frequency=40     # the same overrides work for videos
```

A still is exactly the frame the video shows at that time.

### Using the video in iMovie

1. Put the background video on the timeline.
2. Drag the spectrum video above it, at the same start position.
3. In the video overlay settings, choose **Blue/Green Screen**.

Effects such as blur can be added in the editor. The app keeps the lines plain by default so they key cleanly; its
own glow (section 4) is off unless a preset turns it on.

### Choosing the output format

| `--codec` | File | Size (4 min, 1080p30) | When to use |
|---|---|---|---|
| `h264` (default) | `.mp4` | about 85 MB | Everyday use. Keys well in iMovie. |
| `prores` | `.mov` (ProRes 422) | about 1 GB | Editors that prefer ProRes. Keying quality is similar to H.264 for thin lines. |
| `prores4444` | `.mov` (ProRes 4444) | about 2 GB | Exact colors at line edges, for the cleanest key. |

A 4-minute song renders in about 2 minutes at 1080p30 on an M1 Mac.

### Transparent background

With `--background transparent --codec prores4444` the video has an alpha channel instead of a key color: the
background is fully transparent and the edges of the lines are partly transparent. Place it above the background
video without a keying effect. Nothing mixes with a key color, so colored lines and soft edges come out exactly as
drawn. Use it with editors that read alpha in ProRes 4444; an editor that ignores alpha shows a black background.
Files are larger than opaque ProRes 4444 (a 30-second 1080p30 clip: about 360 MB against 260 MB).

`still` accepts `--background transparent` as well and writes PNG images with alpha.

## 3. Command reference

### `render`

```
audio-spectrum render AUDIO... [options]
```

| Option | Default | Meaning |
|---|---|---|
| `AUDIO...` | | One or more audio files: WAV, AIFF, FLAC, MP3, or anything ffmpeg can read |
| `-o, --output FILE` | next to the input | Output file; only with a single input |
| `--out-dir DIR` | next to each input | Output folder, created if missing. Outputs are named `<input name>_spectrum.mp4` (or `.mov`) |
| `--overwrite` | off | Replace existing outputs. Without it, an existing output is an error for that file and is left untouched |
| `--preset NAME_OR_FILE` | `default` | Built-in or user preset name, or a path to a `.toml` preset file |
| `--set KEY=VALUE` | | Change one preset key, for example `look.max_height=0.4`; repeatable (see section 4) |
| `--background COLOR` | from the preset | `blue`, `green`, `#RRGGBB`, or `transparent` (needs `--codec prores4444`; see section 2) |
| `--size SIZE` | `1080p` | `720p`, `1080p`, `1440p`, `2160p` or `WIDTHxHEIGHT` (even numbers) |
| `--fps FPS` | `30` | Frames per second, for example `24`, `29.97`, `60` |
| `--codec CODEC` | `h264` | `h264`, `prores` or `prores4444` (see above) |
| `--crf N` | `14` | H.264 quality from 0 to 51; lower is better and larger |
| `--no-audio` | off | Leave the audio out of the video |
| `--workers N` | `0` (automatic) | Render processes; `1` renders in a single process |
| `--progress MODE` | `text` | `text` on stderr, `json` events on stdout, or `none` |
| `--fail-fast` | off | Stop at the first file that fails; otherwise the remaining files are still rendered |
| `--start SECONDS` | `0` | Render only part of each song, from this time. The part begins with the frame the full video shows at that time, and the audio is cut to match, so it stays in sync |
| `--duration SECONDS` | to the end | Length of that part |

### `still`

```
audio-spectrum still AUDIO --at SECONDS [--at SECONDS ...] [options]
```

Writes the frame shown at each time as a PNG image named `<input name>_<seconds>s.png` (for example
`song_61.5s.png`) and prints each written path on stdout. The images are lossless and identical to the frames of a
video rendered with the same options.

| Option | Default | Meaning |
|---|---|---|
| `AUDIO` | | One audio file |
| `--at SECONDS` | | Time of a frame, from 0 up to the length of the audio; repeatable |
| `--out-dir DIR` | next to the input | Output folder, created if missing |
| `--overwrite` | off | Replace existing images. Without it, nothing is written when one of the images exists |
| `--preset`, `--set`, `--background`, `--size`, `--fps` | | As for `render`. `--fps` matters because smoothing depends on the frame rate |

Exit codes are those of `render`: 1 when an image exists, the audio cannot be decoded or a time is outside the
audio; 2 for bad options or an invalid preset.

### `gui`

```
audio-spectrum gui [--port PORT] [--no-browser]
```

Starts the local web UI and opens it in the default browser. It needs the `gui` extra: `uv sync --extra gui`
(without it, `gui` exits with code 2 and says so). The server listens on `127.0.0.1` only, on a free port unless
`--port` is given, and stops with Ctrl+C. The address it prints carries a session token; other web pages cannot use
the server without it.

The page, in Japanese, English or Spanish (chosen at the top right; the first visit follows the browser's language):

- **Song**: open an audio file with the Finder dialog, or paste its path and press Enter.
- **Preset**: start from a built-in preset and change any key in the sections below (colors, analysis, look,
  effects). Every key shows its label and a short help text; ranges are checked as in preset files, and a value out
  of range is marked next to its field.
- **Output**: size, frame rate, format, and a transparent background with ProRes 4444. They set the preview's size
  and frame rate.
- **Preview**: the frame at the chosen time, updated as settings change, drawn by the same code as the video (a
  transparent background shows on a checkerboard). "Play 5-second clip" renders five seconds with sound from that
  time; clips are always shown on the preset's background. Warnings from `presets check` appear below.

- **Save preset**: saves the current settings under the name in the Preset box as a user preset (section 4). It
  then appears under "Your presets" in the list, and `--preset NAME` finds it on the command line.
- **Render**: renders the whole song with the current settings and output options, next to the song or into a
  folder chosen with "Choose folder…". The progress shows while it runs; "Cancel" stops it and leaves no file.
  When it is done, "Show in Finder" selects the video. One render runs at a time; stopping the server with Ctrl+C
  cancels a running render cleanly.

### `presets`

```
audio-spectrum presets list          # built-in presets, then user presets
audio-spectrum presets show NAME     # print a built-in preset as TOML
audio-spectrum presets check FILE    # validate a preset file
```

`presets check` also prints warnings on stderr for presets that are valid but likely to key or encode badly: a line
color close to the background, thin colored lines (see section 4), a glow on a key-color background, or blocks
with too many bands. Warnings do not
change the exit code. They are checked against the preset's own background, not a `--background` given to `render`.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | All files rendered |
| 1 | At least one file failed; the others were rendered unless `--fail-fast` was given |
| 2 | Usage error: bad options or an invalid preset. Nothing was rendered |
| 3 | ffmpeg is not installed. Nothing was rendered |
| 130 | Interrupted with Ctrl+C or a termination signal |

### Safe output

Each video is written to a hidden temporary file in the output folder (`.<name>.partial-<number>.mp4`) and renamed
only after ffmpeg succeeds. After a failure or an interruption no output and no temporary file remain, so any file
with the final name is complete. Images from `still` are written the same way.

## 4. Presets

A preset describes the look: how the audio is analyzed and how the lines are drawn. Output settings (size, frame
rate, format) are command options, so one preset works for any output.

Built-in presets:

| Name | Look |
|---|---|
| `default` | 512 white lines on blue, mirrored around a centered baseline, low to high frequencies left to right |
| `bars` | 64 solid white bars, mirrored around a centered baseline |
| `blocks` | 48 bars split into blocks like an LED meter, rising from a baseline near the bottom |
| `glow` | `default` with a soft glow; check keying, or use a transparent background (section 4) |
| `unity-classic` | An approximation of the earlier Unity-based look: tilted perspective, linear frequencies, left channel |

### User presets

Presets saved from the GUI are user presets: TOML files in `~/Library/Application Support/audio-spectrum/presets/`
(or the folder in the environment variable `AUDIO_SPECTRUM_PRESET_DIR`). They are used by name like the built-in
ones (`--preset "My look"`) and listed by `presets list` after the built-in names. They hold only the keys that
differ from `default`. Built-in names are reserved: a user preset cannot be saved as `default`, and a file named
like a built-in preset is ignored with a warning, so a name such as `default` always means the same look in scripts.
A preset file can also be copied into the folder by hand.

### Your own preset files

To make your own, start from a built-in one:

```bash
uv run audio-spectrum presets show default > my-look.toml
# edit my-look.toml
uv run audio-spectrum presets check my-look.toml
uv run audio-spectrum render song.wav --preset my-look.toml
```

Rules:

- Keys you leave out take the `default` preset's values, so a preset can be as short as `name = "mine"` plus the
  keys you change.
- Unknown keys, wrong types and out-of-range values are errors that name the key, for example
  `analysis.bandz: Extra inputs are not permitted`.
- `schema_version = 1` marks the file format.
- `--set KEY=VALUE` on `render` and `still` changes one key without editing a file. `KEY` is a dotted name from the
  table below, such as `analysis.min_frequency`, `look.mirror` or `background`. `VALUE` is written as in the file
  (`0.4`, `true`, `"#00FF00"`); a plain word or color needs no quotes. The result is checked like a preset file.
  `look.kind` cannot be changed this way.

Main keys (the file printed by `presets show default` explains each one):

| Key | Meaning |
|---|---|
| `background`, `foreground` | Colors as `"#RRGGBB"` |
| `analysis.bands` | Number of lines ("wave fineness") |
| `analysis.min_frequency`, `max_frequency` | Frequency range in Hz |
| `analysis.frequency_scale` | `"log"` (even spread of low to high) or `"linear"` |
| `analysis.db_floor` | Level shown as zero height; closer to 0 hides quieter sounds |
| `analysis.tilt_db_per_octave` | Lifts high frequencies so the right side is not always low |
| `analysis.channel` | `"mix"`, `"left"` or `"right"` |
| `analysis.attack_seconds`, `release_seconds` | How fast lines rise and fall |
| `analysis.low_fft_size`, `low_crossover_frequency` | Sharper bass: a longer FFT for the bands below the crossover frequency (see below). `0` (default) is off |
| `look.max_height` | Height of a full-scale line on each side, as a fraction of the frame height |
| `look.baseline_y` | Baseline position from the top, as a fraction of the frame height |
| `look.mirror` | Grow up and down (`true`) or only up (`false`) |
| `look.bar_fill` | Line width as a fraction of the space per band |
| `look.response` | Above 1 keeps quiet bands low and lets peaks stand out |
| `look.style` | `"bars"` (one line or bar per band) or `"blocks"` (bars split into segments, like an LED meter) |
| `look.block_height_px`, `block_gap_px` | Blocks: segment height and the gap between segments, in pixels. A segment shows only once the bar reaches its full height |

With the default analysis, one bass note lights a wide, smooth hill at the left end, because the bands there are
narrower than the analysis can resolve. `--set analysis.low_fft_size=16384` analyzes the bands below 250 Hz with a
four times longer window, so bass notes show as separate, narrower peaks: a 60 Hz tone covers 17 lines instead of 61.
The longer window spans more time, so around a kick the bass lines rise about two frames earlier and fall about one
frame later (the peak stays on the kick's frame). `32768` with `low_crossover_frequency = 150` is sharper still,
with more smearing in time. Bands above the cross-fade octave are not affected.

Thin lines and solid bars are both `"bars"`: fewer `analysis.bands` and a larger `look.bar_fill` give solid bars,
for example `--set analysis.bands=64 --set look.bar_fill=0.8`. Blocks read best with 32 to 96 bands.

### Colors and gradients

| Key | Meaning |
|---|---|
| `fill.mode` | `"solid"` (the `foreground` color), `"frequency"` (a gradient from the left edge to the right edge) or `"height"` (from the baseline to a full-scale tip, mirrored with `look.mirror`) |
| `fill.colors` | Gradient colors, at least two, evenly spaced, for example `["#FFFFFF", "#FF00C8"]` |

```bash
uv run audio-spectrum still song.wav --at 30 --set fill.mode=frequency --set 'fill.colors=["#FF00C8", "#FFE000"]'
```

Gradients work with the flat look (all built-in presets except `unity-classic`). Two limits come from keying:

- A color with a hue close to the key color (light blue or purple on blue back, mid green on green back) is removed
  with the background.
- Thin colored lines lose much of their color in H.264, which stores color at a quarter of the resolution: on the
  512 lines of `default`, a pink-to-yellow gradient came out on average 35 levels (of 255) off and tinted blue. White
  lines and solid bars (`bars`, about 6 levels) are hardly affected. For colored thin lines use
  `--codec prores4444`, which keeps them exact.

### Glow

| Key | Meaning |
|---|---|
| `fx.glow_radius_px` | How far a soft halo spreads around the lines, in pixels; `0` (default) turns it off |
| `fx.glow_strength` | Opacity of the halo, from just above 0 up to 1 |

The halo takes the line colors, including a gradient. On a blue or green back it is a mix of the line color and the
key color, which a chroma key cannot always separate: it may leave a colored fringe or cut the halo short. Check the
result in your editor, or render with `--background transparent --codec prores4444` (section 2), where the halo is
the line color with partial transparency. A glow adds about 10 % to the render time.

## 5. Using it from other tools

The CLI and the Python API are the stable interface for scripts and apps that embed this tool.

### JSON progress events

With `--progress json`, the CLI prints one JSON object per line on stdout. Error text still goes to stderr.

| `event` | Fields | When |
|---|---|---|
| `start` | `input`, `output`, `frames`, `index`, `count` | A file starts rendering (`index` counts from 1) |
| `progress` | `input`, `frame`, `frames` | During rendering, at most about four times a second, and at the last frame |
| `done` | `input`, `output`, `seconds` | A file finished |
| `error` | `input` (absent for errors before any file), `code`, `message` | A file failed, or the run could not start |
| `finished` | `succeeded`, `failed` | All files were processed |
| `interrupted` | | The run was interrupted |

Error codes: `decode_failed`, `encode_failed`, `output_exists`, `worker_failed`, `preset_invalid`,
`ffmpeg_not_found`, `time_out_of_range` (`--start` beyond the end of a song).

```json
{"event": "start", "input": "a.wav", "output": "a_spectrum.mp4", "frames": 7644, "index": 1, "count": 2}
{"event": "progress", "input": "a.wav", "frame": 3000, "frames": 7644}
{"event": "done", "input": "a.wav", "output": "a_spectrum.mp4", "seconds": 114.2}
{"event": "error", "input": "b.wav", "code": "decode_failed", "message": "b.wav: cannot decode audio (...)"}
{"event": "finished", "succeeded": 1, "failed": 1}
```

### Python API

The names exported by the `audio_spectrum` package are the public API; everything else may change.

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


if __name__ == "__main__":  # required, see below
    main()
```

- `render_video` raises a subclass of `AudioSpectrumError` on failure: `PresetError`, `DecodeError`, `EncodeError`,
  `OutputExistsError`, `WorkerError`, `FfmpegNotFoundError`, or `Cancelled` when `cancel` returns true. No output
  file is left behind in any of these cases.
- `override_preset(preset, ["look.max_height=0.4"])` applies overrides like `--set` and returns a new preset. It
  raises `PresetError` for an invalid result.
- `render_stills(audio_path, preset, times, width, height, fps)` returns the frames shown at the given times (in
  seconds) as `(height, width, 3)` `uint8` RGB arrays, without writing files. It raises `TimeRangeError` (code
  `time_out_of_range`) for a time outside the audio, and the same decoding errors as `render_video`. It draws in the
  calling process. With `transparent=True` it returns `(height, width, 4)` RGBA arrays with straight alpha.
- `RenderJob(..., start=10.0, duration=5.0)` renders part of a song, like `--start` and `--duration`. The frames
  are identical to those of the full video, and the audio is cut at the same time.
- `Preview(audio_path, fps)` decodes a song once; `preview.frames(preset, times, width, height)` then returns frames
  like `render_stills`, keeping the analysis for the last few analysis settings. A change of the look alone renders a
  1080p frame in about 20 ms. `preview.duration` is the song's length. Not thread-safe.
- `preset_to_toml(preset)` returns the preset as TOML with only the keys that differ from `default`
  (`full=True` writes every key); `load_preset` reads it back to an equal preset.
- `encode_png(frame)` returns a frame (RGB, or RGBA with alpha) as lossless PNG bytes.
- `save_user_preset(preset, overwrite=False)` writes a preset into the user folder and returns its path;
  `user_preset_names()`, `shadowed_user_preset_names()` and `user_preset_folder()` describe the folder.
  `load_preset(name)` finds user presets by name after the built-in ones.
- `preset_schema()` returns the JSON schema of a preset: types, ranges, defaults and a description of every key,
  with colors as `"#RRGGBB"` strings. `preset_warnings(preset)` returns the warnings of `presets check` as a list.
- A transparent background is an output setting: `EncodeSettings(codec="prores", prores_profile=4, alpha=True)` in
  `RenderJob.encode`. Other codecs with `alpha=True` raise `ValueError`.
- Frames are drawn in several processes, which re-import the calling script. A script must therefore call the API
  under `if __name__ == "__main__":`. Without it the render fails with a `WorkerError` that says so. Passing
  `workers=1` avoids extra processes.

## 6. Troubleshooting

| Problem | What to do |
|---|---|
| `ffmpeg is not installed` (exit code 3) | `brew install ffmpeg` |
| `already exists` | Add `--overwrite`, or choose another `--out-dir` |
| `cannot decode audio` | Check that the file plays; convert it to WAV if needed |
| A preset error naming a key | Fix that key; `presets check FILE` shows all problems at once |
| Lines look soft or bluish after keying | Try `--codec prores4444` |
| Colored lines look washed out or bluish | Thin colored lines lose color in H.264: use `--codec prores4444`, or fewer bands with a larger `look.bar_fill` |
