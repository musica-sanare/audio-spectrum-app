[Docs index](../en/README.md)

# Phase 0 plan: foundation and spike

Status: approved by the owner on 2026-10-25.

## Goal

Set up the repository and prove the core approach before building features: exact offline rendering with ffmpeg, a
look that matches the reference frames, and acceptable speed on the M1. Requirements:
[REQUIREMENTS.md](REQUIREMENTS.md).

## Steps

1. Repository foundation
   - `pyproject.toml` (Python 3.13, `uv`), `src/audio_spectrum/` package, `tests/`.
   - `.gitignore`: OS files (`.DS_Store`), virtual environments, caches, audio and video files, a local `work/`
     directory for inputs and outputs.
   - `CLAUDE.md` (project instructions, `## Overrides of shared rules: None.`).
   - Thin `README.md` / `README.ja.md`, docs indexes `docs/en/README.md` / `docs/ja/README.md`.
   - `docs/working/DECISIONS.md` (ADR log) recording the decisions in REQUIREMENTS.md §6.
   - License: MIT.
2. Spike: analysis
   - Decode audio, mix channels, compute one spectrum per frame time `n / fps`.
   - Log-frequency bands and smoothing; a Unity-like linear mode for `unity-classic`.
   - Unit tests with synthetic signals (sine tones and sweeps land in the expected band).
3. Spike: rendering
   - Render still frames for `default` and `unity-classic` at 1920×1080.
   - Compare OpenCV and Skia for line quality (anti-aliasing) and speed; pick one.
   - Compare `unity-classic` with the owner's reference frames by eye.
4. Spike: encoding and sync
   - Pipe raw frames into ffmpeg (H.264 and ProRes 422), mux the source audio.
   - Verify with `ffprobe` that frame count and duration match the audio; check sync on a click-track test signal.
   - Measure render speed for a 4-minute song at 1080p30 (single process and parallel).
5. Keying check (owner)
   - Overlay a test clip on a background in iMovie with Blue Screen and Green Screen; report edge quality.
6. Results
   - `docs/working/PHASE0_RESULTS.md`: measurements, chosen drawing library, sample-frame observations, open issues.
   - Proposal for the Phase 1 (MVP CLI) plan.

## Test data

- Automated tests use generated signals only.
- Manual checks use the owner's songs from a local folder outside version control. Rendered files go to the ignored
  `work/` directory.

## Commits

Proposed per milestone after the owner's review: (1) foundation and docs, (2) spike code with tests, (3) results.

## Done when

- A 1080p30 H.264 file renders from a real song with exact duration and visible sync.
- The `default` look is approved by the owner from sample frames.
- Speed is measured and the renderer choice is recorded in DECISIONS.md.
