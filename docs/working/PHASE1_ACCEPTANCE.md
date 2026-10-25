[Docs index](../en/README.md)

# Phase 1 acceptance: MVP CLI

Status: accepted by the owner on 2026-10-25. Version 0.2.0.

Plan: [PHASE1_PLAN.md](PHASE1_PLAN.md). Machine: Apple M1 (8 cores), 16 GB RAM, ffmpeg 9.0.2.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| Plan | `d4f3004` | Approved Phase 1 plan |
| 1. Presets as files | `6fddad1` | TOML presets validated with pydantic, built-in presets as files, `presets list/show/check`, `--preset` by name or path (ADR-009) |
| 2. CLI contract | `cbdf5bf` | Batch rendering, `--out-dir`, `--overwrite`, `--fail-fast`, `--progress text/json/none`, exit codes, temporary-file output, Ctrl+C and SIGTERM handling, cancellation, public Python API |
| 3. Stable docs | `fcd0715` | [User guide](../en/USER_GUIDE.md), [Architecture](../en/ARCHITECTURE.md) and [Development](../en/DEVELOPMENT.md) in English and Japanese; version 0.2.0 |

## 2. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| All Must requirements F1–F9 work from the CLI | Met | See section 3 |
| `default` output identical to Phase 0 | Met | Analysis values and rendered frames of both built-in presets hashed before and after milestone 1 on a real song clip: identical |
| Phase 0 sync and frame-count tests still pass; a full song renders within its own length (N3) | Met | `tests/test_video.py` passes; real songs rendered in 43–54 % of their length (section 4) |
| A batch of at least three real songs renders in one command; the owner uses one result in iMovie | Met | Three songs in one `render --out-dir --progress json` run, exit code 0; the owner used the results in iMovie without problems |
| Ctrl+C leaves no output or temporary file | Met | `test_interrupting_the_cli_exits_130_and_leaves_no_files` sends SIGINT and SIGTERM to a running CLI: exit code 130, only the input file remains, no traceback |
| Embedding check: a script uses the public API, and a shell script uses `--progress json` and exit codes | Met | Throwaway scripts outside the repository (not committed): the API rendered a file and refused to overwrite it; the shell script read the events (`start`, `done`, `error` with `decode_failed`, `finished`) and exit codes 1 and 2 |

## 3. Requirements coverage (Must)

| Requirement | Status |
|---|---|
| F1 Input: WAV, AIFF, FLAC, MP3 | WAV, M4A and MP3 tested with generated files; AIFF and FLAC go through libsndfile like WAV |
| F2 Exact duration and timing, audio muxed in | Click-track tests at 30, 60 and 29.97 fps; `--no-audio` |
| F3 Blue, green or any color | `--background blue/green/#RRGGBB`, preset colors |
| F4 Resolution presets and custom size | `--size 720p/1080p/1440p/2160p/WxH` |
| F5 Frame rate, default 30 | `--fps`, exact fractions such as 30000/1001 |
| F6 H.264 with selectable quality | `--crf 0–51`, default 14; ProRes 422 and 4444 as well |
| F7 Built-in presets `default` and `unity-classic` | Shipped as TOML files |
| F8 CLI with batch mode and a stable contract | Batch, JSON events, exit codes, presets by path |
| F9 Presets as editable TOML files | `presets show` to copy, `presets check` to validate |

## 4. Measurements (batch of three real songs, 1080p30, H.264, automatic workers)

| Song length | Frames | Render time | Share of length | Size |
|---|---|---|---|---|
| 318.4 s | 9551 | 172.8 s | 54 % | 76 MB |
| 279.1 s | 8373 | 119.0 s | 43 % | 98 MB |
| 254.8 s | 7644 | 113.5 s | 45 % | 85 MB |

The first song ran while the test suite was running in parallel, which explains its higher share. In every output
the video and audio durations differ by less than one frame. The run emitted 1431 progress events over about
400 seconds, within the limit of about four per second.

Test suite at acceptance: 78 tests, all passing.

## 5. Findings during Phase 1

- **Worker processes and scripts.** With several workers, frames are drawn in processes that re-import the calling
  script. A script that calls the API without an `if __name__ == "__main__":` guard broke the worker pool. The
  pipeline now raises `WorkerError` with the fix in its message, and the user guide documents the rule.
- **CRF range.** ffmpeg 9 accepted a CRF above 51 without an error, so the CLI now validates 0–51 itself.
- **Chapter tracks.** Found in Phase 0: WAV cue chunks became a text track; they are dropped.

## 6. Open items and candidates for the next phases

- Effects and styles (F10–F12): color and gradient, glow and blur, bar styles such as blocks, adjustable frequency
  range from the CLI. The owner currently adds effects in iMovie.
- Smoother low-frequency bands (multi-resolution analysis), noted in [Phase 0 results](PHASE0_RESULTS.md) §7.
- HEVC and alpha output (F13).
- GUI as a local web UI (F14), then optionally a native window and a Finder quick action (F15).
- A user preset folder (deferred by the owner's decision in Phase 1).
