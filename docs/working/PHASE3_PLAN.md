[Docs index](../en/README.md)

# Phase 3 plan: GUI as a local web UI

Status: approved by the owner on 2026-10-26 with the recommended options. P3, P6 and P7 are open (`要確認`); see
"Decisions on open questions".

## Goal

Requirement F14: `audio-spectrum gui` opens a local web page in the browser to choose an audio file and a preset,
set the background, size, frame rate and output format, adjust the look with previews rendered by the same code as
the final output, start and cancel renders with progress, and save the settings as a preset file. The GUI only
exposes what the core and CLI can do and holds no rendering logic of its own (ADR-008, Architecture §3 invariant 4).

Inputs: [Requirements](REQUIREMENTS.md) F14, F15, N6; [Decisions](DECISIONS.md) ADR-008, ADR-009;
[Phase 2 acceptance](PHASE2_ACCEPTANCE.md) §7; [Architecture](../en/ARCHITECTURE.md) §1, §3, §5.

## Before starting

Phase 2 is implemented but not yet accepted (Q1 and the editor checks). Phase 3 can start in parallel: nothing in
it depends on those answers. The Phase 2 acceptance is closed in its own commit whenever the owner has checked.
(要確認 P1)

## Scope

### In

1. A `gui` command that starts a local server and opens the page in the default browser (F14).
2. Core additions the GUI needs, all public and usable by other embedding apps too: rendering a time range,
   previews with a cached analysis, writing a preset as TOML, a machine-readable preset schema, and public keying
   warnings (section 2).
3. The page: file selection, look settings, still and clip previews, render with progress and cancel, save preset.
4. GUI dependencies in an optional extra, so the core and CLI install without them (N6).
5. User guide, architecture and development docs in English and Japanese; an ADR for the GUI's design; version 0.4.0.

### Out (later or not planned)

- F15: a native window (pywebview) and a Finder quick action. The page is built so a native window can show it
  later without changes. (要確認 P2)
- HEVC output, peak hold, glow for the perspective look.
- Several renders at once: rendering already uses all CPU cores, so the GUI runs one job at a time.

## Design

### 1. Architecture

```
browser page (HTML, CSS, JS shipped in the package)
        │  HTTP on 127.0.0.1 only, with a per-session token
        ▼
audio_spectrum.gui (FastAPI app, optional extra)  ──▶  public API of audio_spectrum  ──▶  core
```

- `audio_spectrum/gui/` is a separate subpackage that imports only the public API. Importing `audio_spectrum`
  never imports FastAPI; a test guards this.
- Dependencies in the extra `gui`: `fastapi` and `uvicorn`. Install with `uv sync --extra gui`. Without the extra,
  `audio-spectrum gui` exits with code 2 and says how to install it.
- One process: the server runs renders in a background thread; `render_video` still draws frames in worker
  processes as for the CLI.
- Fully offline: the page loads no fonts, scripts or styles from the network.

### 2. Core additions (public API and CLI)

| Addition | Why | Contract change |
|---|---|---|
| Time range: `RenderJob.start` and `RenderJob.duration` (seconds), CLI `--start` and `--duration` | Short clip previews; also the Q5 test clips from Phase 2 | Additive. Frame `n` shows the audio at `start + n / fps`; the audio is trimmed to the same range. Sync tests extended with click tracks |
| `Preview`: decodes and analyzes a song once, then renders frames for any look at any time | Stills in about 85 ms instead of 0.7 s (decode 0.3 s and analysis 0.4 s per call on a 4-minute song); re-analyzes only when analysis settings or the frame rate change | New class; `render_stills` stays as it is |
| `preset_to_toml(preset)` | Save presets from the GUI | New function (section 6) |
| `preset_schema()` | Build the forms | New function returning the JSON schema of `Preset`, with field descriptions and colors as `#RRGGBB` strings (today the schema has no descriptions and shows colors as integer triples) |
| `preset_warnings(preset)` | Show keying warnings next to the settings | Made public; unchanged behavior |

### 3. The page

Options for how the page is built:

| Option | For | Against | Recommendation |
|---|---|---|---|
| A. Plain HTML, CSS and JavaScript files in the package, no build step | No second toolchain; nothing to install or update besides Python; easy to read and change | Hand-written DOM code; no component framework | **Recommended** |
| B. A framework with a build step (for example Vite with React or Svelte) | Richer components | Node.js toolchain and lockfile next to `uv`; built files to keep in sync; ADR-008 rejected a second stack | Not recommended |

Forms:

| Option | For | Against | Recommendation |
|---|---|---|---|
| A. Generated from `preset_schema()`: one section per table (`analysis`, `look`, `fill`, `fx`), the control chosen by type (number with its range, on/off, choice list, color picker, list of colors) | New preset keys appear in the GUI without GUI changes; ranges and help texts come from one place | Generic layout; labels come from key names and descriptions | **Recommended**, with a short hand-written "main settings" area on top (preset, background, size, frame rate, format) |
| B. Every control written by hand | Freer layout | Must be updated with every new key; easy to drift from the schema | Not recommended |

Layout: settings on the left, preview on the right (a still at the chosen time, with a time slider, and a "play
clip" button), render controls and progress at the bottom. Warnings from `preset_warnings` show next to the preview.

UI language: 要確認 P3 (Japanese, English, or both with a switch).

### 4. Choosing files

A web page cannot read a local file path: a file input only uploads the content, and it cannot pick an output
folder at all.

| Option | For | Against | Recommendation |
|---|---|---|---|
| A. Native macOS dialogs opened by the local server (`osascript`, "choose file" and "choose folder"), plus a path field for pasting | Real paths, the usual Finder dialog, no upload; output can go next to the input as with the CLI | macOS only (the owner's only platform); the dialog may open behind the browser window | **Recommended** |
| B. Upload the file into the server | Works in any browser and system | Copies every song; output still needs a folder; more code for temporary files | Not recommended |
| C. A file browser drawn in the page | Platform-independent | Much UI to build; exposes directory listings over HTTP | Not recommended |

(要確認 P4)

### 5. Previews

- **Stills** through `Preview` at the output size, shown scaled in the page, so pixel settings (line width, blocks)
  look as in the final video. Updated after each settings change, debounced.
- **Clips**: a few seconds around the chosen time rendered with `--start` and `--duration` into a temporary H.264
  file with audio, played in the page. Takes a few seconds; shows its own progress.
- Transparent output previews on a checkerboard.

### 6. Saving presets

- `preset_to_toml` writes TOML with a small writer of our own (the standard library reads TOML but cannot write it;
  our presets use only numbers, booleans, strings, lists and tables). A round-trip test loads every built-in preset,
  writes it and reads it back. Alternative: the `tomli-w` package (small and widely used, but one more dependency).
- What to write (要確認 P5):

| Option | For | Against | Recommendation |
|---|---|---|---|
| A. Only the keys that differ from `default`, plus `name` and `schema_version` | Short files that show what makes the look; follows later changes of defaults | A reader must know the defaults (`presets show default`) | **Recommended** |
| B. Every key | Self-contained | Long; freezes every default | Possible as an option |

- Where to save (要確認 P6):

| Option | For | Against | Recommendation |
|---|---|---|---|
| A. Anywhere, chosen in a save dialog; presets are loaded by path as today | No new rules; no change to `--preset` | Saved presets do not show up in a list by name | Simplest |
| B. A user preset folder (`~/Library/Application Support/audio-spectrum/presets/`), listed by name in the GUI and accepted by `--preset NAME` | Saved looks are one click away in the GUI and the CLI | A CLI contract change (name lookup order: built-in first, or user first); was deferred in Phase 1 | **Recommended** if presets will be reused often |

### 7. Renders

- Start a render of the selected file with the current settings; one job at a time.
- Progress polled by the page about four times a second (the same rate as the CLI's JSON events); cancel uses
  `render_video`'s `cancel` callback, which leaves no output or temporary file.
- A finished render shows the output path and a "Show in Finder" button (`open -R`).
- Batch rendering of several files stays a CLI feature in this phase.

### 8. Local security

A page from any website can send requests to `127.0.0.1`. Without protection it could start renders or write
files through the GUI's server.

- The server listens on `127.0.0.1` only, on a free port (or `--port`).
- `gui` creates a random token per session and opens the page with it; every API request must carry it.
- Requests whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>` are refused (DNS rebinding).
- No cross-origin access (no CORS headers).
- Tests cover each rule.

### 9. Contract changes (all additive)

| Area | Change |
|---|---|
| CLI | `gui` command (needs the `gui` extra); `--start` and `--duration` on `render`; with P6 B, `--preset NAME` also finds user presets |
| JSON events and exit codes | None |
| Public API | `RenderJob.start`, `RenderJob.duration`, `Preview`, `preset_to_toml`, `preset_schema`, `preset_warnings` |
| Preset format | None (`schema_version` stays 1) |

## Milestones and commits

1. **Core additions.** Time range in `RenderJob` and the CLI, `Preview`, `preset_to_toml`, `preset_schema`,
   public `preset_warnings`; user guide. Tests: click-track sync of ranges, previews equal video frames, TOML round
   trip, schema has descriptions and color formats, no change to existing outputs (golden hashes).
2. **Server.** `gui` command and extra, token, host check, endpoints for presets, schema, warnings, file dialogs and
   stills. Tests with FastAPI's test client (`httpx` in the dev group).
3. **Page.** Forms from the schema, main settings, still preview, clip preview, warnings. Checked in the browser.
4. **Renders and saving.** Jobs with progress and cancel, output folder, "Show in Finder", saving presets (and the
   user preset folder if P6 B).
5. **Docs and version.** User guide chapter for the GUI, architecture (layers, `gui` subpackage), development guide
   (running the GUI, its tests), ADR-012 for the GUI design, version 0.4.0.
6. **Acceptance.** `docs/working/PHASE3_ACCEPTANCE.md`.

Each milestone ends with a commit proposal for the owner's approval.

## Acceptance criteria

- `audio-spectrum gui` opens the page; every item of F14 works on the owner's Mac without network access.
- A video rendered from the GUI is frame-for-frame identical to the CLI's with the same settings.
- A preview still is byte-identical to the corresponding video frame; a clip preview stays in sync with its audio.
- Cancelling a render from the GUI leaves no output or temporary file.
- `uv sync` without the extra installs no GUI dependencies, and the CLI and API work as before (all Phase 2 tests
  and golden hashes pass).
- The server refuses requests without the token or with a foreign `Host` header.
- The owner renders at least one song through the GUI and uses it in the editor.

## Decisions on open questions

Answered by the owner on 2026-10-26: the recommended options are approved.

- P1. Phase 3 starts before Phase 2 is accepted; Phase 2 is closed in its own commit after the owner's checks.
- P2. F14 only; a native window (F15) is out of this phase.
- P3. UI language: open, `要確認`. Milestone 3 (the page) waits for it.
- P4. Files are chosen through native macOS dialogs, plus a path field.
- P5. Saved presets contain only the keys that differ from `default`, plus `name` and `schema_version`.
- P6. Where saved presets live: open, `要確認`. Milestone 4 (saving) waits for it.
- P7. Clip preview length: open, `要確認`; 5 seconds until decided.

Milestones 1 and 2 do not depend on the open answers.
