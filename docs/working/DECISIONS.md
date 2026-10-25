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
