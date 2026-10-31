[Docs index](../en/README.md)

# Phase 2 acceptance: effects and styles

Status: accepted by the owner on 2026-10-31. Delivered as version 0.3.0; current version 0.4.0.

Plan: [PHASE2_PLAN.md](PHASE2_PLAN.md). Machine: Apple M1 (8 cores), 16 GB RAM, ffmpeg 9.0.2.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| Plan | `b7df8cf`, `9f82e7d`, `013f047` | Approved plan; the owner's answers to Q1–Q6 |
| 1. Tools and guard | `a5d46f3` | `still` command and `render_stills`, `--set` and `override_preset`, `TimeRangeError`, golden-hash test of the built-in presets |
| 3. Bar styles | `9e6df7a`, `b084285` | `look.style = "blocks"` with segment height and gap; built-in presets `bars` and `blocks` |
| 2. Color | `0cd9705` | `[fill]` gradients across frequencies or along the height; keying warnings in `presets check` |
| Q6. Transparent output | `dbe7448` | `--background transparent` with ProRes 4444 alpha, RGBA stills, ADR-010 |
| 2. Glow | `830bbae` | `[fx]` glow, built-in `glow` preset, glow warning, ADR-011 |
| 4. Low frequencies | `3f16fa1` | Optional multi-resolution analysis for the low bands (`analysis.low_fft_size`) |
| 5. Version | this commit | Version 0.3.0; this report |

Milestones ran in a different order than planned because Q1 and Q2 were first deferred: the work that did not depend
on them went first.

## 2. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| F10–F12 work from preset files and `--set`: gradient fill, glow, bars and blocks, frequency range, low-frequency resolution | Met | Section 3; tests in `test_render.py`, `test_presets.py`, `test_analysis.py`, `test_stills.py` |
| With every new key at its default, frames of `default` and `unity-classic` are byte-identical to Phase 1 | Met | Analysis values and frames of a real clip hashed before milestone 1 and after every milestone: identical. A full song rendered by the Phase 1 code and by 0.3.0 gives the same H.264 frames. `tests/test_golden.py` guards all built-in presets |
| A still is byte-identical to the corresponding video frame | Met | `test_stills_equal_the_video_frames_drawn_by_parallel_workers`; a real-clip still equals frame 450 |
| Sync, frame-count and CLI contract tests pass; a full song with glow renders within its own length (N3) | Met | Tests pass; a 254.8 s song with glow rendered in 155 s (H.264) and 230 s (transparent ProRes 4444), section 5 |
| The owner has checked glow and the low-frequency option in an editor and decided Q1 and Q2 | Met | The owner checked the outputs in an editor and closed the phase on 2026-10-31. Q2: glow off by default, with a warning. Q1: `default` stays as it is; the low-frequency analysis remains an option (section 7) |
| Docs in English and Japanese match the delivered contract | Met | User guide, architecture and development docs updated in the commit of each change; Japanese source hashes current |

Test suite: 160 tests, all passing (78 at the end of Phase 1).

## 3. Requirements coverage

| Requirement | Status |
|---|---|
| F10 Visual options | Color and gradient (`[fill]`), line thickness and gap (`look.bar_fill`, `min_bar_width_px`), bar count (`analysis.bands`), height scale (`look.max_height`), mirror, baseline position, glow (`[fx]`), smoothing (`attack_seconds`, `release_seconds`). Blur is left to the editor (Q3) |
| F11 Bar styles | Thin lines (`default`), solid bars (`bars`), segmented blocks (`blocks`) |
| F12 Frequency axis | Log or linear, any range, from a preset or `--set analysis.min_frequency=...` |
| F13 More output formats | ProRes 4444 with alpha (`--background transparent`). HEVC not done (out of scope) |
| Phase 0 results §7, smooth low-frequency hump | `analysis.low_fft_size`, off by default |

## 4. Contract changes (all additive)

| Area | Change |
|---|---|
| CLI | `still` command; `--set KEY=VALUE` on `render` and `still`; `--background transparent` (with `--codec prores4444`); warnings on stderr from `presets check` |
| JSON events and exit codes | None |
| Public API | `render_stills`, `override_preset`, `TimeRangeError` (code `time_out_of_range`), `EncodeSettings.alpha` |
| Preset format | `look.style`, `look.block_height_px`, `look.block_gap_px`, `[fill]`, `[fx]`, `analysis.low_fft_size`, `analysis.low_crossover_frequency`; `schema_version` stays 1, and Phase 1 presets load and render unchanged |
| Built-in presets | `bars`, `blocks`, `glow` added; `default` and `unity-classic` unchanged |

## 5. Measurements

### Full song (254.8 s, 1080p30, automatic workers)

| Look and output | Render time | Share of length | Size |
|---|---|---|---|
| `default`, H.264 | 142 s | 56 % | 84 MB |
| `default` with `low_fft_size = 16384`, H.264 | 143 s | 56 % | 87 MB |
| `glow`, H.264 | 155 s | 61 % | 113 MB |
| `glow`, transparent ProRes 4444 | 230 s | 90 % | 2.68 GB |

In every output the video and audio durations differ by less than one frame (254.800 s against 254.783 s). The
machine was busier than in Phase 1: the Phase 1 code took 157 s for the same song in the same session, against
113.5 s in [Phase 1 acceptance](PHASE1_ACCEPTANCE.md) §4, so the shares above are pessimistic. The H.264 video of
`default` from the Phase 1 code and from version 0.3.0 is identical frame for frame.

### Effects and analysis

| Item | Result |
|---|---|
| Glow, 30-second clip | 21 s against 19 s without glow (about +10 %) |
| Thin colored lines (512-line gradient), mean error per channel after a round trip | H.264 35 of 255 levels, tinted blue; ProRes 4444 0.9. Solid bars (`bars`) in H.264: 5.7 |
| Transparent output, 30-second clip | 8-bit alpha: 33 s, 364 MB. 16-bit alpha: 81 s, 507 MB, at most 1 level different. Opaque ProRes 4444: 256 MB |
| Low frequencies, lines above half height for a 60 Hz tone | 61 (off), 17 (`low_fft_size = 16384`), 7 (32768 below 150 Hz) |
| Low frequencies, kick at frame 30 visible on frames | 30–32 (off), 28–33 (16384), 27–35 (32768) |
| Low frequencies, analysis of a 30-second clip | 0.05 s (off), 0.17 s (16384), 0.28 s (32768) |

## 6. Findings during Phase 2

- **skia-python and shaders.** `Paint.setShader(None)` is rejected, so a solid fill keeps the original paint and a
  gradient uses a copy. The golden-hash test caught the first attempt.
- **Straight alpha for free.** Skia surfaces on NumPy arrays store unpremultiplied alpha, which is what ffmpeg's
  `rgba` input and PNG expect; no conversion is needed.
- **Alpha bit depth.** 16-bit ProRes alpha was 2.5 times slower and 40 % larger than 8-bit for no visible gain.
- **Colored thin lines in H.264.** White lines survive 4:2:0 well; colored 2 px lines do not. Documented, warned in
  `presets check`, and `--codec prores4444` recommended.
- **Level matching for the long FFT.** A longer FFT reads broadband sound about 6 dB lower. Matching by the median
  ratio over the cross-fade octave, limited to the physical range, keeps noise within about 1 dB. A first test for
  a "seam" at the crossover passed even without level matching, because the cross-fade turns a level step into a
  slope; it was replaced by a level test that fails without matching.

## 7. Open items and candidates for the next phase

- Q1: the owner closed the phase without changing `default`; `analysis.low_fft_size` stays an opt-in key. Adopting
  it in `default` later would change the settled look: a new ADR and renewed golden hashes.
- The owner checked transparent output and glow in an editor before accepting.
- Done in Phase 3 since this report was drafted: the GUI (F14), public `preset_warnings`, a user preset folder,
  `--start`/`--duration` ([Phase 3 acceptance](PHASE3_ACCEPTANCE.md)).
- Later: HEVC output (F13), peak hold.
