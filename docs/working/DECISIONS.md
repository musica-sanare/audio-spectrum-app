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
