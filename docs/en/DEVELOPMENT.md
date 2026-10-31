English | [日本語](../ja/DEVELOPMENT.md) · [Docs index](README.md)

# Development

Setup, checks and conventions for working on the code. For using the tool, see the [user guide](USER_GUIDE.md); for
the structure, see the [architecture](ARCHITECTURE.md).

## 1. Setup

```bash
brew install uv ffmpeg
uv sync
```

Python 3.13 and all dependencies are managed by `uv` (`pyproject.toml`, `uv.lock`). Add a dependency with
`uv add <package>`; keep the core's dependencies few and widely used. GUI dependencies belong to the `gui` extra
(`uv add --optional gui <package>`). The `dev` group includes that extra, so `uv sync` installs everything needed
for development and the tests; an app that embeds this one installs it without the `dev` group and gets the core
dependencies only.

## 2. Tests

```bash
uv run pytest
```

- Tests use generated signals only (`tests/signals.py`); never add real songs to the repository.
- Tests that call ffmpeg are skipped when it is not installed.
- What the main test files cover:

| File | Covers |
|---|---|
| `test_analysis.py` | Frame count, band placement, dB scale, tilt, smoothing, channels |
| `test_audio.py` | Decoding WAV, M4A and MP3; missing files |
| `test_presets.py` | Built-in presets, partial and invalid preset files, `presets` commands |
| `test_render.py` | Geometry of both looks, rendered frames |
| `test_video.py` | Frame count, duration, start times and click-track sync in real videos; codecs |
| `test_cli_contract.py` | JSON events, exit codes, overwrite rules, safe output, cancellation, Ctrl+C and SIGTERM |
| `test_stills.py` | `still` and `render_stills` (identical to video frames), `--set` and `override_preset` |
| `test_golden.py` | Golden hashes of the built-in presets' frames, so a settled look cannot change by accident |
| `test_gui.py` | GUI server: token and host checks, presets, schema, warnings, dialogs (faked), stills; the core never imports the GUI packages. Skipped without the `gui` extra |

## 3. Visual checks

To look at a preset or a change, render stills with `audio-spectrum still` ([user guide](USER_GUIDE.md) §3).
`bench/render_compare.py` renders sample frames of several variants side by side and times the renderer:

```bash
uv run python bench/render_compare.py song.wav --preset default --bands 256 1024 --times 30 60
```

Output goes to `work/render_compare/`. The `work/` folder is ignored by Git; keep songs and rendered videos there or
outside the repository.

When a change should not alter the look (refactoring), compare frames before and after for the same input, for
example by hashing rendered frames, and say so in the commit message. `tests/test_golden.py` does this for the
built-in presets on a generated signal. When a look changes on purpose, or a Skia or NumPy upgrade changes the bytes,
check the frames visually first and then renew the hashes it prints.

## 4. Conventions

- Code, comments, commit messages and docs are in English. Japanese appears only in the `docs/ja/` translations and
  `README.ja.md`.
- Keep the [invariants](ARCHITECTURE.md#3-invariants).
- A new preset key needs a label and a help text in each of `src/audio_spectrum/gui/static/i18n/en.json`, `ja.json`
  and `es.json`, and new page texts need an entry in all three; `test_gui.py` fails otherwise.
- Stable docs live in `docs/en/` with a Japanese twin in `docs/ja/` that records the English blob hash on its first
  line. Working docs (plans, results, decisions) live in `docs/working/` in English only.
- Work proceeds in phases: a plan in `docs/working/PHASE<N>_PLAN.md` approved by the owner, then implementation with a
  commit per milestone, then an acceptance report.
