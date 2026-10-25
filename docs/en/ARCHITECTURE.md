English | [日本語](../ja/ARCHITECTURE.md) · [Docs index](README.md)

# Architecture

How the renderer is built, the rules every change must keep, and where new features plug in. Design decisions and
their reasons are in the [decision log](../working/DECISIONS.md).

## 1. Layers

```
  GUI (later, optional extra)        CLI (cli.py)              other apps and scripts
            \                           |                            /
             +------------- public Python API (audio_spectrum) -----+
                                        |
                                   core library
```

- **Core library.** Analysis, rendering and encoding. No UI code and no UI dependencies.
- **CLI.** A thin layer that parses arguments, calls the core and reports progress, errors and exit codes. It is the
  stable contract for tools in other languages.
- **GUI.** Planned as a local web UI on the same API, installed as an optional extra
  ([Requirements](../working/REQUIREMENTS.md) F14, ADR-008).

## 2. Data flow

```
audio file ──load_audio──▶ samples ──analyze──▶ band values (frames × bands)
                                                     │
                                  for each frame n:  ▼
                              geometry (quads) ──raster (Skia)──▶ RGB frame (RGBA when transparent)
                                                     │
                                                     ▼
                         ffmpeg (raw RGB pipe + source audio) ──▶ temporary file ──rename──▶ video
```

| Module | Role |
|---|---|
| `audio.py` | Decodes audio with libsndfile, or ffmpeg for other formats; selects or mixes channels |
| `analysis.py` | One spectrum per frame time `n / fps`: window centered on that time, FFT (optionally a longer one for low bands, level-matched and cross-faded), frequency bands, dB scale, tilt, attack/release smoothing |
| `presets.py` | Preset schema (pydantic), loading of built-in and user TOML files, overrides and keying warnings |
| `builtin_presets/` | The built-in presets as TOML files |
| `geometry.py` | Turns one frame of band values into quads in pixel coordinates, per look (flat, perspective) and style (bars, blocks); places fill gradients |
| `raster.py` | Fills quads with anti-aliasing (Skia) into an RGB frame, in a solid color or a linear gradient; with a transparent background, an RGBA frame with straight alpha |
| `renderer.py` | Combines geometry and raster for one frame |
| `encode.py` | Builds the ffmpeg command; `VideoWriter` streams frames, writes to a temporary file and renames it on success; `write_png` writes stills the same way |
| `pipeline.py` | `render_video`: load, analyze, render frames (in parallel worker processes), encode; progress and cancellation. `render_stills`: single frames for checks |
| `errors.py` | Error types with stable codes |
| `cli.py` | Commands, progress output, exit codes, signal handling |

## 3. Invariants

Every change must keep these:

1. **Exact sync.** Frame `n` shows the audio at time `n / fps`. The number of frames is `ceil(samples × fps / rate)`.
   Rendering never depends on real-time playback or on machine speed. Tested with click tracks in
   `tests/test_video.py`.
2. **Determinism.** The same input, preset and options give the same frames, in one process or many.
3. **No partial outputs.** A file with the final output name is always complete. Failures, cancellation and
   interruptions leave no output or temporary file.
4. **The core has no UI code.** The CLI and the GUI only call the public API and add no rendering logic.
5. **Presets describe the look only.** Output settings (size, frame rate, codec) stay outside presets.
6. **Repository safety.** No songs, rendered videos or personal data in the repository; tests use generated signals.

## 4. Performance

Analysis of a whole song takes well under a second. Drawing takes about 13 ms per 1080p frame on one core.
`render_video` draws frames in worker processes (CPU cores minus one by default), at most a few chunks ahead of
ffmpeg so memory stays bounded. With parallel workers the H.264 encoder is the limit: a 4-minute song renders in about
2 minutes at 1080p30 on an M1. Measurements: [Phase 0 results](../working/PHASE0_RESULTS.md).

## 5. Extension points

| To add | Where |
|---|---|
| A new look (for example circular, blocks) | A look model in `presets.py` with a new `kind`, and its quad builder in `geometry.py`. The raster backend and the rest stay unchanged |
| New analysis options | Fields in `AnalysisSettings` (with defaults, so old presets keep working) and their use in `analysis.py` |
| Effects such as glow | Drawn by the raster backend together with the shapes (`raster.py`), configured in the preset's `[fx]` table (ADR-011). Effects that depend on earlier frames belong in the analysis |
| A new output format | `EncodeSettings` and `build_command` in `encode.py`, plus a `--codec` choice in `cli.py` |
| A GPU or 3D renderer | Another rasterizer or renderer behind the same `render(values) -> frame` call |
| The GUI | A separate package module using only the public API, with its dependencies in an optional extra |

When a change alters the preset format incompatibly, raise `schema_version` and keep reading version 1 files.
