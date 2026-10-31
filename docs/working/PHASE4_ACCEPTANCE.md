[Docs index](../en/README.md)

# Phase 4 acceptance: drawing the spectrum over another app's frames

Status: accepted by the owner on 2026-10-31. Version 0.5.0.

Plan: [PHASE4_PLAN.md](PHASE4_PLAN.md). Machine: Apple M1 (8 cores), 16 GB RAM, ffmpeg 9.0.2.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| Plan | `4170bad` | Approved plan (option B: a backdrop for `render_video`) |
| 1. Backdrop | `aa23794` | `RenderJob.backdrop`, the `Backdrop` protocol, `BackdropError`; drawing over supplied pixels in the workers; backdrops for `render_stills` and `Preview.frames`; user guide with a tested example in English, Japanese and Spanish |
| 2. Docs and version | `5039cd7` | Architecture in three languages, ADR-013, version 0.5.0 |
| 3. Acceptance | this commit | This report |

## 2. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| With no backdrop, every output is unchanged | Met | Golden hashes of all five built-in presets; a backdrop of the preset's color gives byte-identical frames for `default`, `glow`, `blocks` and `unity-classic`, in one process and in parallel (`test_a_backdrop_of_the_preset_color_changes_nothing`); the full suite passes |
| A backdrop's frames reach the video in sync with the audio, for whole songs and parts, in one or many processes | Met | `test_backdrops_get_the_index_and_time_of_every_frame` (each frame's index and `index / fps` checked in the backdrop); `test_a_part_of_the_song_passes_whole_song_frame_numbers` (a part from 1.0 s decodes to frames 30–44); `test_stills_with_a_backdrop_equal_the_video_frames`; the real song below ends within one frame of its audio |
| A failing backdrop leaves no output or temporary file | Met | `test_a_failing_backdrop_leaves_no_file` (a backdrop that raises and one that returns the wrong size, in one process and in parallel) |
| A 4-minute song with a still-image backdrop renders in less than its own length at 1080p30 (N3) | Met | A 317.7 s song with a 5000 × 3333 JPEG backdrop: 182.1 s (57 %), section 4 |

Test suite: 237 tests, all passing (219 at the end of Phase 3).

## 3. Contract changes (all additive)

| Area | Change |
|---|---|
| Public API | `RenderJob.backdrop`, `Backdrop`, `BackdropError`; `backdrop` on `render_stills` and `Preview.frames` |
| Error codes | `backdrop_failed` (only through the API) |
| CLI, JSON events, exit codes, presets, GUI | None |

## 4. Measurements

A real song (317.7 s, 44.1 kHz, 24-bit WAV) and a photo (5000 × 3333 JPEG), 1080p30, H.264 CRF 14, automatic workers,
run one after another with nothing else running. The backdrop is the user guide's `StillImage` example.

| Render | Time | Share of length | Size |
|---|---|---|---|
| `default`, no backdrop | 151.9 s | 48 % | 108 MB |
| `default` over the photo | 182.1 s | 57 % | 209 MB |
| `glow` over the photo | 179.0 s | 56 % | 250 MB |

In all three the video lasts 317.767 s and the audio 317.746 s, less than one frame apart.

## 5. Findings

- **Cost of a backdrop.** Drawing over a detailed photo adds about 20 % to the render time, mostly in the encoder:
  the photo needs about twice the bits of a flat background at the same quality. Blending in the main process
  instead would have cost about 46 ms per frame (the reason for drawing in the workers, ADR-013).
- **The user guide's example stretches images.** It resizes the image to the frame size, so this 3:2 photo was
  stretched to 16:9. Fine as a minimal example; lyrics-video-app should scale and crop instead.
- **work/ was cleaned up during the phase**, so the usual real-clip hash comparison could not run for milestone 1;
  the golden hashes and the backdrop identity tests cover the same ground.

## 6. Open items

- 要確認 P4-1: tagging `v0.5.0` for lyrics-video-app, or keeping its path dependency for now.
- Next: lyrics-video-app in its own repository, which will use this backdrop.
