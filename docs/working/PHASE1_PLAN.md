[Docs index](../en/README.md)

# Phase 1 plan: MVP CLI

Status: approved by the owner on 2026-10-25.

## Goal

Turn the Phase 0 spike into a dependable command-line tool that covers all Must requirements (F1–F9), and make the
CLI and the Python API a stable contract that other apps can embed (N6). No new visual features: FX, the GUI and
alpha output come in later phases.

Inputs: [Requirements](REQUIREMENTS.md), [Decisions](DECISIONS.md), [Phase 0 results](PHASE0_RESULTS.md).

## Scope

### In

1. Presets as TOML files with a validated schema (F7, F9).
2. The CLI contract (F8): batch rendering, machine-readable progress, documented exit codes, presets by name or path.
3. Safe output: no partial files after a failure or Ctrl+C, no silent overwrites.
4. A small public Python API for embedding.
5. Stable docs in English and Japanese: user guide (including the CLI reference), architecture and development guide.

### Out (later phases)

- FX and new styles (F10–F12), HEVC and alpha output (F13), GUI (F14–F15).
- The smoother low-frequency analysis noted in Phase 0 results §7.

## Design

### 1. Presets as files

- Format: TOML, read with the standard library (`tomllib`).
- Validation: a pydantic model. Unknown keys, wrong types and out-of-range values fail with a message naming the key.
  Pydantic is chosen because it gives clear errors and a JSON schema that the GUI can reuse to build its forms
  (ADR-009, to be added).
- Built-in presets `default` and `unity-classic` ship as TOML files inside the package.
- `--preset` takes a built-in name or a file path. A user preset folder is deferred to a later phase (owner's
  decision).
- A preset holds the look only: analysis settings, layout and colors. Output settings (size, frame rate, codec,
  quality) stay CLI options, so one preset works for any output.
- Each file has `schema_version = 1`, so later phases can change the format without breaking old presets.

Example:

```toml
schema_version = 1
name = "default"
background = "#0000FF"
foreground = "#FFFFFF"

[analysis]
bands = 512
frequency_scale = "log"
min_frequency = 30.0
max_frequency = 16000.0
db_floor = -48.0
tilt_db_per_octave = 3.0
channel = "mix"
attack_seconds = 0.01
release_seconds = 0.15

[look]
kind = "flat"
margin_x = 0.04
baseline_y = 0.5
max_height = 0.3
mirror = true
bar_fill = 0.5
response = 1.6
```

### 2. Commands

```
audio-spectrum render AUDIO... [options]   render one or more files
audio-spectrum presets list                list built-in presets
audio-spectrum presets show NAME           print a preset as TOML, to copy and edit
audio-spectrum presets check FILE          validate a preset file
```

`render` options: as in Phase 0 (`--preset`, `--background`, `--size`, `--fps`, `--codec`, `--crf`, `--no-audio`,
`--workers`), plus:

| Option | Meaning |
|---|---|
| `-o, --output FILE` | Output file; only with a single input |
| `--out-dir DIR` | Output folder for one or more inputs (default: next to each input) |
| `--overwrite` | Replace existing outputs. Without it, an existing output is an error for that file |
| `--progress {text,json,none}` | Progress format (default `text`) |
| `--fail-fast` | Stop the batch at the first failed file (default: continue with the rest) |

### 3. Progress and exit codes

- `--progress text`: a human progress line on stderr.
- `--progress json`: JSON Lines on stdout, one event per line; stderr carries only error text:

```json
{"event": "start", "input": "a.wav", "output": "a_spectrum.mp4", "frames": 7644, "index": 1, "count": 2}
{"event": "progress", "input": "a.wav", "frame": 3000, "frames": 7644}
{"event": "done", "input": "a.wav", "output": "a_spectrum.mp4", "seconds": 124.3}
{"event": "error", "input": "b.wav", "code": "decode_failed", "message": "..."}
{"event": "finished", "succeeded": 1, "failed": 1}
```

- Progress events are throttled, at most a few per second.
- Exit codes:

| Code | Meaning |
|---|---|
| 0 | All files rendered |
| 1 | At least one file failed (details in the error events or on stderr) |
| 2 | Usage error: bad options or an invalid preset |
| 3 | ffmpeg is missing |
| 130 | Interrupted (Ctrl+C or SIGTERM) |

### 4. Safe output

- Each video is written to a temporary file in the output folder and renamed to the final name only after ffmpeg
  succeeds. A failure or interruption removes the temporary file, so a final-named file is always complete.
- Ctrl+C or SIGTERM stops the worker processes and ffmpeg and then exits with 130.

### 5. Public Python API

Exported from `audio_spectrum`, documented, and covered by tests:

- `load_preset(name_or_path) -> Preset`
- `RenderJob` and `EncodeSettings`
- `render_video(job, progress=None, cancel=None) -> RenderResult`, where `cancel` is a callable checked between
  frames (the GUI uses it later)
- The error types: `PresetError`, `DecodeError`, `EncodeError`, `FfmpegNotFoundError`, `Cancelled`

Everything else is internal and may change.

### 6. Code layout

- `cli.py` holds argument parsing and output formatting; `__main__.py` only calls it.
- `presets.py` turns into a loader and schema; the built-in TOML files live in `audio_spectrum/presets/`.
- `errors.py` holds the error types; the CLI maps them to exit codes in one place.
- The core modules (`audio`, `analysis`, `geometry`, `raster`, `renderer`, `encode`, `pipeline`) keep no CLI or UI
  code.

## Milestones and commits

1. **Presets as files.** Schema, built-in TOML presets, `presets list/show/check`, `--preset` by path. Tests: built-in
   presets load and render exactly as in Phase 0, and invalid files give clear errors.
2. **CLI contract.** Batch mode, `--out-dir`, `--overwrite`, `--progress`, exit codes, safe output and cancellation,
   public API. Tests: JSON event sequence, every exit code, no file left after a forced failure and after an
   interruption, a batch where one file fails.
3. **Stable docs.** `docs/en/USER_GUIDE.md` (setup, everyday use, CLI reference with options, progress events and
   exit codes, preset format), `docs/en/ARCHITECTURE.md` (layers, data flow, invariants, extension points) and
   `docs/en/DEVELOPMENT.md` (setup, tests, bench script), with Japanese twins and both indexes updated. `CLAUDE.md`
   "Read first" points to them. The version becomes 0.2.0.
4. **Acceptance.** `docs/working/PHASE1_ACCEPTANCE.md`: results against the criteria below and the owner's check.

Each milestone ends with a commit proposal for the owner's approval.

## Acceptance criteria

- All Must requirements F1–F9 work from the CLI. MP3 input is checked with a generated file.
- `default` output is identical to Phase 0 for the same input and options (no visual change from the refactoring).
- Sync and frame-count tests from Phase 0 still pass, and a full song still renders within its own length (N3).
- A batch of at least three real songs renders in one command. The owner uses one result in iMovie.
- Ctrl+C during a render leaves no output or temporary file behind.
- Embedding check: a throwaway script outside the package renders through the public API, and a shell script uses
  `--progress json` and the exit codes. Neither is committed.

## Decisions on open items

- User preset folder: deferred to a later phase.
- Batch behavior on failure: continue with the remaining files by default; `--fail-fast` stops at the first failure.
