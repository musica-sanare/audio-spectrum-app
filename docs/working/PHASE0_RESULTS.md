[Docs index](../en/README.md)

# Phase 0 results

Status: complete (2026-10-25). Phase 0 is done.

Plan: [PHASE0_PLAN.md](PHASE0_PLAN.md). Machine: Apple M1 (8 cores), 16 GB RAM, ffmpeg 9.0.2.

## 1. Summary

- Offline frame-by-frame rendering works end to end: audio file in, H.264 or ProRes video out with the source audio.
- Sync is exact by construction and verified automatically (section 4).
- A 255-second song renders at 1080p30 in about 2 minutes, half its own length (section 5). Target N3 is met.
- Skia is the drawing library (section 3).
- The `default` look uses 512 bands, white lines on pure blue. Approved by the owner from sample frames.
- The owner checked 30-second clips in iMovie and found them good as raw material (section 6).

## 2. Analysis

- The window is centered on each frame time `n / fps`.
- Analysis takes about 0.4 s for a 5-minute song, so it is not a bottleneck.
- On real songs, a plain 60 dB scale kept most bands at 40–60 % height, and high frequencies read low. The `default`
  preset therefore uses a 48 dB range, a +3 dB/octave tilt around 1 kHz and a response exponent of 1.6, so quiet
  bands stay low and peaks stand out.
- Low bands below about 200 Hz are narrower than one FFT bin at 4096 points and are interpolated, which draws a smooth
  hump at the left end. A multi-resolution analysis could sharpen it later.

## 3. Rendering: OpenCV versus Skia

1920×1080, about 250–350 visible quads per frame, one process:

| Library | Time per frame | Edges |
|---|---|---|
| Skia 144.1 | 13–15 ms | Crisp; a 2 px line stays 2 px |
| OpenCV 5.0 | 12 ms | Softer; lines grow by about 1 px |

Speed is similar. Skia was chosen because crisp, exact edges key better. OpenCV was removed from the dependencies.

`unity-classic`, which reuses the legacy camera position, pitch and field of view, matches the reference frames
closely, including the slanted lines. Its start position and baseline height differ slightly from the reference,
probably because of how the reference was cropped. That is acceptable for a comparison preset.

## 4. Encoding and sync

Automated tests in `tests/test_video.py` use a generated click track and check:

- The frame count equals `ceil(duration × fps)` at 30, 60 and 29.97 fps.
- The video and audio both start at 0, and the video duration equals the audio duration within one frame.
- Each click shows on the frame of its time, with at most one frame of offset. Nothing shows three frames before it.
- Parallel rendering produces the same frames as a single process.

A chapter text track copied from WAV cue chunks was found in the first real-song output and is now dropped.

## 5. Speed and size (real song, 254.8 s, 1080p30, 7644 frames)

| Output | Workers | Time | Peak memory | Size |
|---|---|---|---|---|
| H.264 CRF 14 | 1 | 172 s | 0.65 GB | 85 MB |
| H.264 CRF 14 | 7 (automatic) | 124–129 s | 1.05 GB | 85 MB |
| ProRes 422 | 7 | 180 s | — | 1.03 GB |

For 30-second clips, ProRes 4444 took about 25 s and produced about 256 MB.

With parallel workers, the x264 encoder is the limit rather than drawing.

## 6. Keying quality

Round trip of one 1080p frame. The values are the mean RGB of pixels that are pure white in the source:

| Format | Line pixels | Background |
|---|---|---|
| H.264 4:2:0 | 248, 250, 255 | 1, 0, 254 |
| ProRes 422 | 246, 248, 255 | 0, 0, 252 |
| ProRes 4444 | 254, 255, 255 | 0, 0, 255 |

Thin vertical lines lose horizontal color resolution in both 4:2:0 and 4:2:2, so ProRes 422 does not help this look.
ProRes 4444 keeps it exact and was added as `--codec prores4444`.

iMovie check (owner): 30-second clips in H.264, ProRes 422 and ProRes 4444, on blue and on green, overlaid on a
background with iMovie's blue/green screen. The owner found them good as raw material and reported no keying problems.
Plain lines without effects are preferred for now; blur and similar effects are added in iMovie until the app offers
them (requirement F10). H.264 stays the default.

## 7. Open issues

- Low bands are interpolated into a smooth hump (section 2). Revisit with a multi-resolution analysis if it bothers
  the owner.
- The spike CLI has no batch mode, preset files, machine-readable progress or documented exit codes yet.

## 8. Proposed next: Phase 1 (MVP CLI)

- Presets as TOML files with a validated schema; built-in presets shipped as files.
- The CLI contract from [Requirements](REQUIREMENTS.md) F8: batch mode, `--progress json`, documented exit codes,
  `--preset` taking a file path.
- Cancellation and clean-up of partial output files.
- Stable docs: user guide, architecture and development guide (English and Japanese).
