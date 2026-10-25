[Docs index](../en/README.md)

# Requirements

Status: approved by the owner on 2026-10-25. Open items are marked `要確認`.

## 1. Purpose

Generate an audio spectrum video from an audio file, to be overlaid on a separately made background video (lyrics and
so on) in a video editor. The spectrum is rendered on a solid key color (blue back or green back) and the background is
removed with a chroma key in the editor.

This replaces a legacy Unity 2019.2 project that played the song in real time and captured the screen with Unity
Recorder. That workflow has three problems this app must solve:

- Starting a game engine and recording in real time is slow and heavy.
- Real-time capture lets audio and video drift apart, so every video needs manual alignment.
- The old engine version and heavy engine dependency are hard to maintain.

## 2. Scope and constraints

- Runs fully locally on the owner's machine (Apple Silicon M1, 16 GB RAM, macOS). No network access during normal use.
  Not a public web service.
- Prefer platform-independent code and libraries, but only the owner's Mac must be supported.
- The repository and its full history must be safe to publish on GitHub: no songs, rendered videos, reference frames,
  local absolute paths, or personal data.
- The legacy Unity project stays outside version control and will be deleted later.

## 3. Users and workflow

- Single user: the owner, editing in iMovie.
- Typical flow: audio file (song master) → spectrum video on blue or green → iMovie "Green/Blue Screen" overlay on the
  background video → export.
- Usual output: 1920×1080, 16:9.

## 4. Functional requirements

### 4.1 Must (MVP)

- F1. Input: WAV, AIFF, FLAC and MP3.
- F2. Output: a video whose duration and timing match the input audio exactly (see N1), with the original audio
  muxed in (can be turned off).
- F3. Background: blue, green, or any solid color. Default pure blue `#0000FF`.
- F4. Resolution: presets (720p, 1080p, 1440p, 2160p) and custom size. Default 1920×1080.
- F5. Frame rate: 24, 25, 30, 50, 60 and custom. Default 30.
- F6. Quality: H.264 with selectable quality (CRF or bitrate). Default H.264 at a high quality setting suited to
  keying.
- F7. Built-in style presets:
  - `default`: the improved look (see 4.3).
  - `unity-classic`: an approximation of the legacy look, kept for comparison.
- F8. Command-line interface. One command renders one file; a batch mode renders several files with the same preset.
  The CLI is the stable contract for other tools and apps that embed this one (see N6): machine-readable progress
  (`--progress json`), documented exit codes, and presets given as file paths.
- F9. Presets are plain text files (TOML) that the owner can copy and edit.

### 4.2 Should (after MVP)

- F10. Visual options (FX): bar color or gradient, line thickness, bar count ("wave fineness"), gap, height scale,
  mirror on/off, baseline position, glow, blur, smoothing (rise and fall speed).
- F11. Bar styles: thin lines (default), solid bars, segmented blocks ("block" style).
- F12. Frequency axis: logarithmic (default) or linear; adjustable frequency range.
- F13. More output formats: ProRes 422 (better keying quality, supported by iMovie), HEVC, and ProRes 4444 with alpha
  for editors that support transparency.
- F14. GUI as a local web UI (`audio-spectrum gui` opens it in the browser): choose the audio file and preset, set
  background, size, frame rate and output format, adjust FX with previews as still frames or short clips rendered by
  the same code as the final output, start and cancel renders with progress, and save settings as a preset file. The
  GUI only exposes what the CLI and core can do; it adds no rendering logic of its own.
- F15. Optional later: show the same web UI in a native window (pywebview) for a native file dialog, and a Finder
  quick action that renders the selected audio files with a chosen preset.

### 4.3 The improved default look

Based on the legacy output (white thin vertical lines on blue, mirrored up and down around a horizontal baseline) with
these fixes:

- Show the whole audible range (about 30 Hz to 16 kHz) on a logarithmic axis spread across the full width, instead of
  only about 0–3 kHz on a linear axis with most bins off screen.
- Analyze a mix of both channels instead of the left channel only.
- Apply light smoothing so lines do not flicker frame to frame.
- Flat 2D layout (no camera tilt), horizontally centered, with configurable margins.
- No glow by default: glow blends with the key color and keys badly in iMovie (see section 7).

## 5. Non-functional requirements

- N1. Sync: frame `n` shows the audio at time `n / fps` exactly. The video duration equals the audio duration within
  one frame. No lead-in silence by default (the legacy 5-second wait is not needed); an optional lead-in is set in
  whole frames.
- N2. Determinism: the same input and preset produce the same frames.
- N3. Performance target: a 4-minute song at 1080p30 renders in no more than its own length on the M1
  (要確認 after the Phase 0 measurement).
- N4. Maintainability: few, widely used dependencies; Python managed with `uv`; ffmpeg as an external tool;
  automated tests that need no real songs (synthetic signals only).
- N5. Extensibility: analysis, rendering and encoding are separate components. New styles, renderers (for example a
  GPU 3D renderer later) and output formats plug in without reworking the rest.
- N6. Embeddability: three layers. The core is a Python library with no UI dependencies; the CLI and the GUI are thin
  entry points on top of it. GUI dependencies are an optional extra (for example `audio-spectrum-app[gui]`), so another
  app can embed the core and CLI (as a Git submodule or a Git dependency) without them.

## 6. Technology decisions (proposed)

| Area | Choice | Reason |
|---|---|---|
| Language | Python 3.13, `uv` | Same toolchain as the owner's other projects; strong numeric libraries |
| Audio decoding | `soundfile` (WAV/AIFF/FLAC); ffmpeg for MP3 and others | Exact sample access |
| Analysis | NumPy FFT | Simple, fast, deterministic |
| Rendering | CPU 2D drawing (OpenCV or Skia, decided in Phase 0) | No GPU or engine dependency; enough for the target look |
| Encoding | ffmpeg via a raw-frame pipe (libx264, ProRes, VideoToolbox) | Industry standard; exact frame timing |
| Presets | TOML, validated by a typed schema | Readable and editable by hand |
| Interfaces | CLI first; FastAPI local web UI later, optionally in a pywebview window | Same stack as the owner's other project; one UI for browser and window |

Rejected: browser 3D (Three.js) with headless Chromium, and Remotion (heavy dependencies, slower export, Remotion's
license terms); Godot or Blender (a new engine dependency); Rust (higher maintenance cost for the owner); wgpu 3D
rendering (kept as a possible later renderer, not needed for the target look).

## 7. Known risks and notes

- H.264 stores color at reduced resolution (4:2:0), so thin lines can get soft or tinted edges after keying. Mitigations:
  pure key color, high quality setting, optional ProRes 422 output, line thickness of at least 2 px at 1080p.
- Glow and blur create pixels that mix the line color with the key color. A chroma key cannot separate them cleanly, so
  these effects stay optional and off by default for keyed output.
- Unity's spectrum scaling is not documented exactly; `unity-classic` is an approximation tuned by eye against the
  owner's reference frames (kept locally, not committed).

## 8. Out of scope

- Rendering lyrics or the background video.
- Real-time preview with audio playback (may be reconsidered later).
- Distribution as a packaged app or public service.
