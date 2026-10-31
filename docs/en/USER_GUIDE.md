English | [日本語](../ja/USER_GUIDE.md) · [Docs index](README.md)

# User guide

audio-spectrum-app turns an audio file into a spectrum video on a solid blue or green background, ready to be keyed
over a background video in an editor such as iMovie. Everything runs offline on your Mac. This guide covers setup,
everyday use, the GUI, presets and every command. To call the tool from scripts or other apps, see the
[embedding guide](EMBEDDING.md).

## 1. Setup

You need macOS (tested on an Apple Silicon M1), [Homebrew](https://brew.sh), `uv` and ffmpeg.

```bash
brew install uv ffmpeg
git clone <repository URL> audio-spectrum-app
cd audio-spectrum-app
uv sync
uv run audio-spectrum --version
```

`uv sync` installs Python 3.13 and the libraries into `.venv/` inside the folder, including those of the GUI.
Nothing else on the system changes.

## 2. Everyday use

### Rendering a song

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

Render single frames as PNG images instead of a whole video. Change preset keys on the command line with `--set`:

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

Effects such as blur can be added in the editor. The app keeps the lines plain by default so they key cleanly. Its
own [glow](#glow) is off unless a preset turns it on.

## 3. The GUI

The same settings, with previews, are also available in a local web page:

```bash
uv run audio-spectrum gui
```

It opens in the default browser and runs until you press Ctrl+C in the terminal. The page is in Japanese, English
or Spanish, chosen at the top right; the first visit follows the browser's language.

- **Song**: open an audio file with the Finder dialog, or paste its path and press Enter.
- **Preset**: start from a built-in preset and change any key in the sections below (colors, analysis, look,
  effects).
  - Every key shows its label and a short help text.
  - Ranges are checked as in preset files. A value out of range is marked next to its field.
- **Output**: size, frame rate, format, and a transparent background with ProRes 4444. They also set the preview's
  size and frame rate.
- **Preview**: the frame at the chosen time, updated as settings change.
  - It is drawn by the same code as the video. A transparent background shows on a checkerboard.
  - "Play 5-second clip" renders five seconds with sound from that time. Clips are always shown on the preset's
    background.
  - Warnings from `presets check` appear below.
- **Save preset**: saves the current settings as a [user preset](#user-presets), under the name in the Preset box.
  It then appears under "Your presets" in the list, and `--preset NAME` finds it on the command line.
- **Render**: renders the whole song with the current settings and output options.
  - The video goes next to the song, or into a folder chosen with "Choose folder…".
  - The progress shows while it runs. "Cancel" stops it and leaves no file.
  - When it is done, "Show in Finder" selects the video.
  - One render runs at a time. Stopping the server with Ctrl+C cancels a running render cleanly.

Options for starting the GUI: [`gui`](#gui).

## 4. Output formats

### Choosing a codec

H.264 is right for everyday use; ProRes 4444 gives the cleanest key at a much larger size.

| `--codec` | File | Size (4 min, 1080p30) | When to use |
|---|---|---|---|
| `h264` (default) | `.mp4` | about 85 MB | Everyday use. Keys well in iMovie. |
| `prores` | `.mov` (ProRes 422) | about 1 GB | Editors that prefer ProRes. Keying quality is similar to H.264 for thin lines. |
| `prores4444` | `.mov` (ProRes 4444) | about 2 GB | Exact colors at line edges, for the cleanest key. |

A 4-minute song renders in about 2 minutes at 1080p30 on an M1 Mac.

### Transparent background

With `--background transparent --codec prores4444`, the video has an alpha channel instead of a key color. Place it
above the background video without a keying effect.

- The background is fully transparent, and the edges of the lines are partly transparent.
- Nothing mixes with a key color, so colored lines and soft edges come out exactly as drawn.
- Use it with editors that read alpha in ProRes 4444. An editor that ignores alpha shows a black background.
- Files are larger than opaque ProRes 4444: a 30-second 1080p30 clip takes about 360 MB against 260 MB.

`still` accepts `--background transparent` as well and writes PNG images with alpha.

## 5. Presets

A preset describes the look: how the audio is analyzed and how the lines are drawn. Output settings (size, frame
rate, format) are command options, so one preset works for any output.

### Built-in presets

| Name | Look |
|---|---|
| `default` | 512 white lines on blue, mirrored around a centered baseline, low to high frequencies left to right |
| `bars` | 64 solid white bars, mirrored around a centered baseline |
| `blocks` | 48 bars split into blocks like an LED meter, rising from a baseline near the bottom |
| `glow` | `default` with a soft glow; check keying, or use a transparent background ([Transparent background](#transparent-background)) |
| `unity-classic` | An approximation of the earlier Unity-based look: tilted perspective, linear frequencies, left channel |

### User presets

Presets saved from the GUI are user presets. They are used by name like the built-in ones (`--preset "My look"`).

- They are TOML files in `~/Library/Application Support/audio-spectrum/presets/`, or in the folder named by the
  environment variable `AUDIO_SPECTRUM_PRESET_DIR`.
- `presets list` lists them after the built-in names.
- They hold only the keys that differ from `default`.
- A preset file can also be copied into the folder by hand.

Built-in names are reserved, so a name such as `default` always means the same look in scripts. A user preset cannot
be saved as `default`, and a file named like a built-in preset is ignored with a warning.

### Your own preset files

To make your own, start from a built-in one:

```bash
uv run audio-spectrum presets show default > my-look.toml
# edit my-look.toml
uv run audio-spectrum presets check my-look.toml
uv run audio-spectrum render song.wav --preset my-look.toml
```

Rules:

- Keys you leave out take the `default` preset's values. A preset can be as short as `name = "mine"` plus the keys
  you change.
- Unknown keys, wrong types and out-of-range values are errors that name the key, for example
  `analysis.bandz: Extra inputs are not permitted`.
- `schema_version = 1` marks the file format.
- `--set KEY=VALUE` on `render` and `still` changes one key without editing a file.
  - `KEY` is a dotted name from the tables below, such as `analysis.min_frequency`, `look.mirror` or `background`.
  - `VALUE` is written as in the file (`0.4`, `true`, `"#00FF00"`). A plain word or color needs no quotes.
  - The result is checked like a preset file.
  - `look.kind` cannot be changed this way.

### Main keys

The file printed by `presets show default` explains each key.

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
| `analysis.low_fft_size`, `low_crossover_frequency` | Sharper bass: a longer FFT for the bands below the crossover frequency ([Sharper bass](#sharper-bass)). `0` (default) is off |
| `look.max_height` | Height of a full-scale line on each side, as a fraction of the frame height |
| `look.baseline_y` | Baseline position from the top, as a fraction of the frame height |
| `look.mirror` | Grow up and down (`true`) or only up (`false`) |
| `look.bar_fill` | Line width as a fraction of the space per band |
| `look.response` | Above 1 keeps quiet bands low and lets peaks stand out |
| `look.style` | `"bars"` (one line or bar per band) or `"blocks"` (bars split into segments, like an LED meter) |
| `look.block_height_px`, `block_gap_px` | Blocks: segment height and the gap between segments, in pixels. A segment shows only once the bar reaches its full height |

Thin lines and solid bars are both `"bars"`. Fewer `analysis.bands` and a larger `look.bar_fill` give solid bars, for
example `--set analysis.bands=64 --set look.bar_fill=0.8`. Blocks read best with 32 to 96 bands.

### Sharper bass

`--set analysis.low_fft_size=16384` shows bass notes as separate, narrower peaks instead of one wide hill.

- **The problem.** With the default analysis, one bass note lights a wide, smooth hill at the left end. The bands
  there are narrower than the analysis can resolve.
- **The fix.** `16384` analyzes the bands below 250 Hz with a four times longer window. A 60 Hz tone then covers 17
  lines instead of 61.
- **The cost.** The longer window spans more time. Around a kick, the bass lines rise about two frames earlier and
  fall about one frame later; the peak stays on the kick's frame.
- **Sharper still.** `32768` with `low_crossover_frequency = 150` is sharper, with more smearing in time.

Bands above the cross-fade octave are not affected.

### Colors and gradients

| Key | Meaning |
|---|---|
| `fill.mode` | `"solid"` (the `foreground` color), `"frequency"` (a gradient from the left edge to the right edge) or `"height"` (from the baseline to a full-scale tip, mirrored with `look.mirror`) |
| `fill.colors` | Gradient colors, at least two, evenly spaced, for example `["#FFFFFF", "#FF00C8"]` |

```bash
uv run audio-spectrum still song.wav --at 30 --set fill.mode=frequency --set 'fill.colors=["#FF00C8", "#FFE000"]'
```

Gradients work with the flat look (all built-in presets except `unity-classic`). Two limits come from keying:

- A color with a hue close to the key color is removed with the background. That means light blue or purple on blue
  back, and mid green on green back.
- Thin colored lines lose much of their color in H.264, which stores color at a quarter of the resolution. For colored
  thin lines use `--codec prores4444`, which keeps them exact.
  - On the 512 lines of `default`, a pink-to-yellow gradient came out on average 35 levels (of 255) off and tinted
    blue.
  - White lines and solid bars (`bars`, about 6 levels) are hardly affected.

### Glow

| Key | Meaning |
|---|---|
| `fx.glow_radius_px` | How far a soft halo spreads around the lines, in pixels; `0` (default) turns it off |
| `fx.glow_strength` | Opacity of the halo, from just above 0 up to 1 |

Check the result in your editor when you use a glow on a blue or green back.

- The halo takes the line colors, including a gradient.
- On a blue or green back, the halo is a mix of the line color and the key color. A chroma key cannot always separate
  them: it may leave a colored fringe or cut the halo short.
- With `--background transparent --codec prores4444` ([Transparent background](#transparent-background)), the halo is
  the line color with partial transparency.
- A glow adds about 10 % to the render time.

## 6. Troubleshooting

| Problem | What to do |
|---|---|
| `ffmpeg is not installed` (exit code 3) | `brew install ffmpeg` |
| `already exists` | Add `--overwrite`, or choose another `--out-dir` |
| `cannot decode audio` | Check that the file plays; convert it to WAV if needed |
| A preset error naming a key | Fix that key; `presets check FILE` shows all problems at once |
| Lines look soft or bluish after keying | Try `--codec prores4444` |
| Colored lines look washed out or bluish | Thin colored lines lose color in H.264: use `--codec prores4444`, or fewer bands with a larger `look.bar_fill` |
| `the GUI needs the gui extra` | `uv sync --extra gui` |
| `cannot listen on 127.0.0.1:PORT` | Another program uses that port: leave out `--port` to take a free one |
| The page says access was refused | The server was restarted, so its token changed: open the address it printed again |
| The file dialog does not appear | It may be behind the browser window; or paste the file's path into the field and press Enter |

## 7. Command reference

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
| `--set KEY=VALUE` | | Change one preset key, for example `look.max_height=0.4`; repeatable ([Your own preset files](#your-own-preset-files)) |
| `--background COLOR` | from the preset | `blue`, `green`, `#RRGGBB`, or `transparent` (needs `--codec prores4444`; [Transparent background](#transparent-background)) |
| `--size SIZE` | `1080p` | `720p`, `1080p`, `1440p`, `2160p` or `WIDTHxHEIGHT` (even numbers) |
| `--fps FPS` | `30` | Frames per second, for example `24`, `29.97`, `60` |
| `--codec CODEC` | `h264` | `h264`, `prores` or `prores4444` ([Choosing a codec](#choosing-a-codec)) |
| `--crf N` | `14` | H.264 quality from 0 to 51; lower is better and larger |
| `--no-audio` | off | Leave the audio out of the video |
| `--workers N` | `0` (automatic) | Render processes; `1` renders in a single process |
| `--progress MODE` | `text` | `text` on stderr, `json` events on stdout ([embedding guide](EMBEDDING.md#1-json-progress-events)), or `none` |
| `--fail-fast` | off | Stop at the first file that fails; otherwise the remaining files are still rendered |
| `--start SECONDS` | `0` | Render only part of each song, from this time. The part begins with the frame the full video shows at that time, and the audio is cut to match, so it stays in sync |
| `--duration SECONDS` | to the end | Length of that part |

### `still`

```
audio-spectrum still AUDIO --at SECONDS [--at SECONDS ...] [options]
```

Writes the frame shown at each time as a PNG image and prints each written path on stdout.

- Images are named `<input name>_<seconds>s.png`, for example `song_61.5s.png`.
- The images are lossless and identical to the frames of a video rendered with the same options.

| Option | Default | Meaning |
|---|---|---|
| `AUDIO` | | One audio file |
| `--at SECONDS` | | Time of a frame, from 0 up to the length of the audio; repeatable |
| `--out-dir DIR` | next to the input | Output folder, created if missing |
| `--overwrite` | off | Replace existing images. Without it, nothing is written when one of the images exists |
| `--preset`, `--set`, `--background`, `--size`, `--fps` | | As for `render`. `--fps` matters because smoothing depends on the frame rate |

Exit codes are those of `render`:

- 1 when an image exists, the audio cannot be decoded, or a time is outside the audio.
- 2 for bad options or an invalid preset.

### `gui`

```
audio-spectrum gui [--port PORT] [--no-browser]
```

Starts the local web UI ([The GUI](#3-the-gui)) and opens it in the default browser.

- It needs the `gui` extra, which `uv sync` in this folder installs. Elsewhere use `uv sync --extra gui`. Without it,
  `gui` exits with code 2 and says so.
- The server listens on `127.0.0.1` only, on a free port unless `--port` is given, and stops with Ctrl+C.
- The address it prints carries a session token. Other web pages cannot use the server without it.
- `--no-browser` prints the address without opening it.

### `presets`

```
audio-spectrum presets list          # built-in presets, then user presets
audio-spectrum presets show NAME     # print a built-in preset as TOML
audio-spectrum presets check FILE    # validate a preset file
```

`presets check` also prints warnings on stderr for presets that are valid but likely to key or encode badly:

- a line color close to the background;
- thin colored lines ([Colors and gradients](#colors-and-gradients));
- a glow on a key-color background;
- blocks with too many bands.

Warnings do not change the exit code. They are checked against the preset's own background, not a `--background`
given to `render`.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | All files rendered |
| 1 | At least one file failed; the others were rendered unless `--fail-fast` was given |
| 2 | Usage error: bad options or an invalid preset. Nothing was rendered |
| 3 | ffmpeg is not installed. Nothing was rendered |
| 130 | Interrupted with Ctrl+C or a termination signal |

### Safe output

Any file with the final output name is complete.

- Each video is written to a hidden temporary file in the output folder (`.<name>.partial-<number>.mp4`).
- It is renamed only after ffmpeg succeeds.
- After a failure or an interruption, no output and no temporary file remain.
- Images from `still` are written the same way.
