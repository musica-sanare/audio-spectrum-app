[Docs index](../en/README.md)

# Decisions

Architecture decision log. Newest last. Each entry: context, decision, consequences.

## ADR-001: Render offline, frame by frame

- Context: The legacy tool played the song in real time and captured the screen, so audio and video drifted and needed
  manual alignment.
- Decision: Decode the whole audio file and render frame `n` from the audio at time `n / fps`. Pipe frames to ffmpeg
  and mux the source audio.
- Consequences: Sync is exact by construction and independent of machine load. No real-time preview with audio in the
  core path.

## ADR-002: Python, uv and ffmpeg

- Context: The owner wants a local, maintainable tool with few dependencies, and already uses Python with `uv`.
- Decision: Python 3.13 with `uv`; NumPy for analysis; ffmpeg as an external encoder; presets in TOML.
- Consequences: No game engine or browser runtime. ffmpeg must be installed separately (`brew install ffmpeg`).
  Alternatives considered are listed in [Requirements](REQUIREMENTS.md) §6.

## ADR-003: CPU 2D rendering behind a renderer interface

- Context: The target look is a row of lines or bars; it does not need a 3D engine.
- Decision: Render frames on the CPU with a 2D drawing library behind a small renderer interface. The library (OpenCV
  or Skia) is chosen in Phase 0.
- Consequences: Frames are independent, so rendering can run in parallel. A GPU or 3D renderer can be added later
  without changing analysis or encoding.

## ADR-004: Improved look by default, legacy look as a preset

- Context: The legacy output showed only about 0–3 kHz of the left channel on a linear axis, without smoothing.
- Decision: The `default` preset uses a logarithmic axis over about 30 Hz–16 kHz, a mix of both channels and light
  smoothing. `unity-classic` approximates the legacy look.
- Consequences: Existing videos are not reproduced exactly by default; the classic preset exists for comparison.

## ADR-005: Keyed output first, glow off by default

- Context: The owner composites in iMovie, which supports chroma keying but not alpha video. H.264 stores color at
  reduced resolution and glow mixes with the key color.
- Decision: Default to H.264 on pure blue with lines at least 2 px wide at 1080p and no glow. Offer ProRes 422 for
  cleaner keying and, later, ProRes 4444 with alpha for editors that support it.
- Consequences: Glow and blur remain available but may key poorly; documented as a known limitation.

## ADR-006: Skia for rasterization

- Context: ADR-003 left the 2D drawing library open. OpenCV and Skia were compared in Phase 0.
- Decision: Use Skia (`skia-python`). Looks produce library-independent quads in `geometry.py`; `raster.py` fills them.
- Consequences: Crisp, exact anti-aliased edges at a similar speed. Measurements are in
  [Phase 0 results](PHASE0_RESULTS.md) §3.

## ADR-007: ProRes 4444 as the cleanest keyed output

- Context: Thin vertical lines lose horizontal color resolution in H.264 4:2:0 and in ProRes 422 (4:2:2), so line
  pixels mix with the key color. ADR-005 expected ProRes 422 to help, but it does not for this look.
- Decision: Keep H.264 as the default. Offer ProRes 4444 (`--codec prores4444`, full color resolution) for the
  cleanest keying, and keep ProRes 422 for editors that need it.
- Consequences: ProRes 4444 files are about 30 times larger than H.264. See [Phase 0 results](PHASE0_RESULTS.md) §6.

## ADR-008: Core and CLI as the base, GUI as a local web UI

- Context: The owner wants a GUI and plans to embed video generation in a larger automated app later, possibly as a
  Git submodule.
- Decision: Keep three layers: a core library without UI dependencies, a CLI as the stable contract for other tools,
  and a GUI as a local web UI (FastAPI, opened in the browser) that calls the core. GUI dependencies are an optional
  extra. A native window (pywebview) and a Finder quick action may be added later. Qt, Electron and Tauri were
  rejected: heavier dependencies or a second technology stack.
- Consequences: The CLI needs machine-readable progress, documented exit codes and file-based presets (Phase 1). The
  GUI must not hold rendering logic of its own. See [Requirements](REQUIREMENTS.md) F8, F14, F15 and N6.

## ADR-009: Presets as TOML files validated with pydantic

- Context: Presets must be plain files the owner can copy and edit (F9), with clear errors, and the GUI will later need
  a machine-readable description of the settings to build its forms.
- Decision: Presets are TOML files read with the standard library's `tomllib` and validated with pydantic models
  (`AnalysisSettings`, `FlatLook`, `PerspectiveLook`, `Preset`). Unknown keys are errors; missing keys take the
  `default` preset's values; each file carries `schema_version = 1`. Built-in presets ship as TOML files in the
  package.
- Consequences: One new core dependency (pydantic), which FastAPI needs for the GUI anyway. Error messages name the
  key at fault, and the models can produce a JSON schema for the GUI.

## ADR-010: Transparent output as ProRes 4444 with alpha

- Context: Keyed output mixes soft edges, glow and colored lines with the key color (ADR-005, ADR-007). The owner
  wants alpha output even though iMovie is the current editor; the app need not be optimized for iMovie alone. Test
  clips are in [Phase 2 plan](PHASE2_PLAN.md), "Decisions on open questions".
- Decision: `--background transparent` (CLI) or `EncodeSettings(alpha=True)` (API) draws frames on a transparent
  background with straight alpha and encodes ProRes 4444 with 8-bit alpha (`yuva444p10le`, `-alpha_bits 8`).
  Transparency is an output setting, not part of presets. Other codecs refuse it. Keyed H.264 stays the default.
- Consequences: Clean edges, colors and glow in editors that read alpha. Files are about 1.4 times the size of
  opaque ProRes 4444; 16-bit alpha was 2.5 times slower to encode and 40 % larger for no visible gain, since frames
  carry 8-bit alpha.

## ADR-011: Effects drawn with the shapes

- Context: Architecture §5 planned effects such as glow as a post-processing step on the finished RGB frame. At that
  point lines and background are already merged, so a blur would also spread the key color, and a transparent
  background (ADR-010) would need its own path.
- Decision: The raster backend draws effects together with the shapes: the glow is the same path drawn first with a
  blur mask filter (standard deviation a third of `fx.glow_radius_px`) and the fill's color or gradient, then the
  sharp shapes on top. Effects are configured in the preset's `[fx]` table and are off by default. Effects that
  depend on earlier frames go into the analysis, so frames stay independent for parallel rendering.
- Consequences: No extra dependency; a glow adds about 10 % to the render time. The halo is correct on transparent
  backgrounds. On a key-color background it still mixes with the key color, which `presets check` warns about.

## ADR-012: The GUI's design

- Context: ADR-008 chose a local web UI on the core's public API. Phase 3 had to settle how the page is built, how it
  reaches local files, how it is protected from other web pages, which languages it speaks and where saved presets
  live ([Phase 3 plan](PHASE3_PLAN.md)).
- Decision:
  - FastAPI and uvicorn in the optional `gui` extra (also in the `dev` group); the `audio_spectrum.gui` subpackage
    imports only the public API, and importing the core never imports it.
  - The page is plain HTML, CSS and JavaScript without a build step. Its forms are generated from
    `preset_schema()`, so new preset keys appear without GUI code.
  - Local files are chosen through native macOS dialogs opened by the server (`osascript`), plus a path field,
    because a web page cannot read local paths.
  - The server listens on `127.0.0.1` only, refuses foreign `Host` headers (DNS rebinding) and API requests
    without the per-session token, and sends no cross-origin headers.
  - Page texts in Japanese, English and Spanish from one message file per language; a test keeps the files
    complete. Core messages stay in English.
  - Saved presets go to a user folder (`~/Library/Application Support/audio-spectrum/presets`, or
    `$AUDIO_SPECTRUM_PRESET_DIR`) and hold only the keys that differ from `default`; built-in names are reserved.
  - One render at a time, in a background thread, cancelled cleanly when the server stops. Clip previews render in
    one process, which is faster than starting worker processes for 150 frames.
- Consequences: No second toolchain; the GUI's output equals the CLI's frame for frame. File dialogs are macOS-only
  (a path can always be typed). Every new preset key needs a label and help text in three languages. Rejected:
  Qt, Electron and Tauri (ADR-008); a JavaScript framework with a build step; uploading songs into the server.

## ADR-013: A backdrop under the spectrum for embedding apps

- Context: The owner builds lyrics videos from a background image, lyrics captions and this app's spectrum, so far
  by stacking layers in iMovie. A separate repository, lyrics-video-app, will automate that and embed this app
  (ADR-008). Blending a transparent spectrum frame over another picture in NumPy took about 46 ms per 1080p frame,
  more than drawing the spectrum (about 20 ms), and the internal renderer cannot be sent to worker processes
  ([Phase 4 plan](PHASE4_PLAN.md)).
- Decision: `RenderJob.backdrop` takes a picklable object whose `frame(index, seconds, width, height)` returns the RGB
  picture under the spectrum for frame `index` of the whole song. The workers ask for it and draw the spectrum
  directly over it, so `render_video` keeps one path for sync, parallel workers, progress, cancellation, parts of
  songs, audio and safe output. `render_stills` and `Preview.frames` take the same backdrop. Failures raise
  `BackdropError` and leave no file. A backdrop cannot be combined with a transparent background. No layer over the
  spectrum and no CLI option for now.
- Consequences: Lyrics, captions and layout stay in lyrics-video-app; this repository only gains an additive API.
  Drawing over a one-color backdrop gives byte-identical frames, so existing outputs are unchanged. Rejected: making
  the analysis, painter and encoder public for a second render loop (duplicates sync and safety logic), and lyrics
  features in this repository.
