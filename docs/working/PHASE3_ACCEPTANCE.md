[Docs index](../en/README.md)

# Phase 3 acceptance: GUI as a local web UI

Status: accepted by the owner on 2026-10-31. Version 0.4.0.

Plan: [PHASE3_PLAN.md](PHASE3_PLAN.md). Machine: Apple M1 (8 cores), 16 GB RAM, ffmpeg 9.0.2.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| Plan | `8381483`, `686ca3e` | Approved plan; the owner's answers to P1–P7 |
| 1. Core additions | `212a263` | Time ranges (`--start`, `--duration`), `Preview`, `preset_to_toml`, `preset_schema`, public `preset_warnings` |
| 2. Server | `9074f05` | `gui` command and extra, token and host checks, presets, schema, warnings, native file dialogs, stills |
| 3. Page | `bfcf9c6` | Forms from the schema, still and 5-second clip previews, warnings and field errors, Japanese, English and Spanish |
| 4. Renders and saving | `5090c74` | User preset folder with reserved built-in names, saving from the page, background renders with progress, cancel and Show in Finder |
| 5. Docs and version | `6579a07`, `3673b0b` | GUI in the user guide, development guide and architecture, ADR-012, version 0.4.0; Spanish translations of the stable docs |
| 6. Acceptance | this commit | This report |

`b859234` (branch rule in `CLAUDE.md`, requirement N3 resolved) landed between the phases.

## 2. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| `audio-spectrum gui` opens the page; every item of F14 works on the owner's Mac without network access | Met | Checked in a browser on the owner's Mac: song by path, preset changes with field errors, gradients, transparent preview, perspective look, 5-second clip, saving a preset, a full render with progress (section 5). The page loads nothing from the network (no external URL in `gui/static/`) |
| A video rendered from the GUI is frame-for-frame identical to the CLI's with the same settings | Met | A 30-second clip rendered from the page and with `render --preset <saved user preset>`: identical `framemd5` of every frame |
| A preview still is byte-identical to the corresponding video frame; a clip preview stays in sync with its audio | Met | `test_stills_equal_the_core_stills` (through the server), `test_preview_frames_equal_render_stills_and_reuse_the_analysis`; clips use `RenderJob.start`/`duration`, covered by click-track tests (`test_a_part_of_the_song_keeps_frames_and_audio_in_sync`: the click lands within 1 ms in the audio and on its frame) |
| Cancelling a render from the GUI leaves no output or temporary file | Met | `test_a_render_can_be_cancelled_and_only_one_runs_at_a_time`, `test_stopping_the_server_cancels_a_running_render` |
| Without the extra no GUI dependencies are installed, and the CLI and API work as before | Met | `uv sync --no-dev` removes FastAPI and uvicorn, leaving the four core dependencies; `test_the_core_and_cli_do_not_import_the_gui_packages`; golden hashes of all built-in presets unchanged after every milestone |
| The server refuses requests without the token or with a foreign `Host` header | Met | `test_api_requests_need_the_session_token`, `test_requests_to_a_foreign_host_are_refused`, no CORS headers (`test_the_page_loads_without_the_token_but_sends_no_cross_origin_headers`) |
| The owner renders at least one song through the GUI and uses it in the editor | Met | The owner checked it in an editor and closed the phase on 2026-10-31 |

Test suite: 219 tests, all passing (160 at the end of Phase 2).

## 3. Requirements coverage

| Requirement | Status |
|---|---|
| F14 GUI as a local web UI | `audio-spectrum gui`: choose the audio file (native dialog or path) and the preset; background, size, frame rate and output format; FX adjusted with stills and short clips rendered by the same code; renders with progress and cancel; settings saved as a preset file |
| F15 Native window, Finder quick action | Not in this phase (P2) |
| N6 Embeddability | GUI dependencies in the optional `gui` extra; new public API usable by other apps (`Preview`, time ranges, preset writing and schema, user presets) |

## 4. Contract changes (all additive)

| Area | Change |
|---|---|
| CLI | `gui` command; `--start` and `--duration` on `render`; `--preset NAME` and `presets list` include user presets |
| JSON events and exit codes | New error code `time_out_of_range`; exit codes unchanged |
| Public API | `RenderJob.start`, `RenderJob.duration`, `Preview`, `preset_to_toml`, `preset_schema`, `preset_warnings`, `encode_png`, `save_user_preset`, `user_preset_names`, `shadowed_user_preset_names`, `user_preset_folder` |
| Environment | `AUDIO_SPECTRUM_PRESET_DIR` overrides the user preset folder |
| Preset format | None (`schema_version` stays 1); every key now has a description in the schema |
| Dependencies | Optional extra `gui` (fastapi, uvicorn); dev group adds the extra and `httpx` |

## 5. Measurements

| Item | Result |
|---|---|
| `Preview`, 4-minute song | Opening (decode) 0.38 s; first frame 0.39 s; a change of look 21 ms; another analysis setting 0.28 s |
| Still in the page, 1080p | About 0.2 s from request to image (preset, drawing, PNG and transfer) |
| 5-second clip, 1080p | 4.6 s in one process. With worker processes it was 5.1 s, and about 15 s the first time while the workers loaded their libraries, so clips render in one process |
| Full render from the page, 30-second clip with glow, 1080p30 | 22.3 s, frame-identical to the CLI |

## 6. Findings during Phase 3

- **Preset schema for forms.** The schema had no descriptions and showed colors as integer triples; field docstrings
  are now included (21 keys gained a description), colors are `#RRGGBB` strings, and `inf` travels as `"Infinity"`.
- **Audio for parts of a song.** A first version decided "whole song" after slicing the frames, so a part starting
  at 0 would have kept the full audio; caught before testing, and covered by a test since.
- **Tests and the real preset folder.** Once user presets existed, tests would have read the owner's folder; a
  fixture now points every test at a temporary folder.
- **Busy port.** `gui --port` on a port in use ended in a traceback; it is now a message with exit code 2.
- **Layout.** Fieldsets do not shrink below their content by default and spilled into the preview column.
- **Overwrite question.** The page repeated the server's message inside its own question; the server now returns the
  output path separately.
- **Test dependency.** Starlette warns that its test client prefers `httpx2`; adding it was blocked as an unvetted
  package, so `httpx` stays and the owner decides.

## 7. Open items and candidates for the next phase

- 要確認: review of the Japanese texts (page and docs); a native speaker's review of the Spanish texts.
- 要確認: switching the test dependency from `httpx` to `httpx2`.
- Phase 2 was accepted on the same day ([Phase 2 acceptance](PHASE2_ACCEPTANCE.md)).
- The shared documentation rule covers English and Japanese only; adding Spanish there is a change to
  `claude-shared-rules`.
- Candidates: a native window and a Finder quick action (F15); batch rendering in the page; filling two colors when
  a gradient is chosen; translated warning texts; HEVC output; peak hold.
