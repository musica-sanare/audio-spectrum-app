[Docs index](../en/README.md)

# Phase 2 plan: effects and styles

Status: scope approved by the owner on 2026-10-25 (option 1: effects and styles now, GUI in Phase 3). Questions
Q1–Q6 are open and marked `要確認`; milestone 1 does not depend on them.

## Goal

Add the Should requirements for the look (F10–F12): color and gradient, glow, bar styles such as blocks, and frequency
range adjustments, plus a sharper low-frequency analysis (the "smooth hump", [Phase 0 results](PHASE0_RESULTS.md) §7).
Every effect is off by default: with an existing preset the output stays byte-identical to Phase 1. The GUI (F14)
follows in Phase 3 and reuses the tools added here.

Inputs: [Requirements](REQUIREMENTS.md), [Decisions](DECISIONS.md) (ADR-001–009),
[Phase 1 acceptance](PHASE1_ACCEPTANCE.md) §6, [Architecture](../en/ARCHITECTURE.md) §3 and §5.

## Choice of scope

| Option | Content | For | Against | Recommendation |
|---|---|---|---|---|
| 1. FX and styles now, GUI in Phase 3 | A, plus a still-frame preview command and preset overrides on the command line | Settles the preset schema before the GUI builds its forms from it (ADR-009); the preview command is the core of the GUI preview later; small phase, quick acceptance | No GUI for another phase; tuning effects means editing TOML and rendering stills | **Recommended** |
| 2. GUI now, FX in Phase 3 | B | Easier to use sooner | The GUI forms would change again when FX keys arrive; little to adjust in the GUI while the look has few options | Not recommended |
| 3. Both in Phase 2 | A and B | One phase | Large phase with a long time to acceptance; two areas of risk at once (keying of effects, web UI) | Not recommended |

The owner chose option 1; the rest of this plan follows it.

## Scope

### In

1. Sharper low frequencies through a multi-resolution analysis, as an opt-in preset key (section 2).
2. Fill colors: solid (as now) or a gradient across frequencies or along the line height (section 3).
3. Bar styles: bars (as now: thin lines or solid bars, by `bar_fill` and `bands`) and segmented blocks (section 4).
4. Glow, off by default, with a keying check in iMovie before it is finished (section 5).
5. Preset overrides on the command line with `--set KEY=VALUE`, which also covers the frequency range (section 6).
6. A `still` command and API that render single frames as PNG for quick checks (section 7).
7. New built-in example presets and keying warnings in `presets check` (sections 8, 9).
8. User guide, architecture and development docs updated in English and Japanese; version 0.3.0.

### Out (later phases or not planned)

- GUI (F14, F15): Phase 3.
- HEVC and alpha output (F13), unless the owner decides otherwise (要確認 Q6).
- Blur of the lines in the app (要確認 Q3): the owner already blurs in iMovie, after keying, which is cleaner.
- New looks beyond the flat layout (for example circular). Effects apply to the `flat` look; `unity-classic` stays a
  comparison preset without effects.

## Design

### 1. Principles

- **Defaults unchanged.** Every new key has a default that reproduces the Phase 1 look. Old preset files stay valid
  and render the same frames. Verified by frame hashes before and after each milestone (section 10).
- **Additive schema.** New keys only, so `schema_version` stays 1 (Architecture §5: raise it only for incompatible
  changes). A preset that uses new keys is rejected by version 0.2.0 with a clear "extra inputs" error.
- **Effects in the right stage.** Anything that depends on earlier frames (smoothing, a possible peak hold) belongs in
  the analysis, which runs once over the whole song. Rendering stays a pure function of one frame's values, so
  parallel workers and determinism keep working (invariant 2).
- **Keying first.** Colors and glow are checked against the key color; known limits are documented, not hidden
  (ADR-005, ADR-007).

### 2. Low frequencies (the "smooth hump")

Cause: at 4096 points one FFT bin is about 11.7 Hz at 48 kHz, and the Blackman window spreads a pure tone over about
±3 bins. On the log axis the bands below about 875 Hz (276 of 512) are narrower than one bin, so a single bass note
lights a wide, smooth hill.

Spike measurements (generated signals, 48 kHz, default preset; scripts kept outside the repository):

| FFT size (window) | Lines above half height for one tone at 40 / 60 / 100 / 200 Hz | 55 Hz and 73 Hz together | 60 Hz kick at frame 30 is visible on frames | Analysis of 5 min |
|---|---|---|---|---|
| 4096 (85 ms), now | 61 / 61 / 39 / 18 | one merged hill | 30–32 | 0.4 s |
| 8192 (171 ms) | 43 / 30 / 17 / 10 | two peaks, shallow dip | 29–32 | — |
| 16384 (341 ms) | 22 / 16 / 9 / 5 | two separate peaks | 28–33 | 1.0 s |
| 32768 (683 ms) | 11 / 7 / 5 / 3 | two separate peaks | 27–35 | 2.0 s |

Comparison stills from a real clip are in `work/phase2_spike/lowfreq_*.png` (not committed): top is the current
analysis, middle uses 16384 points below 250 Hz, bottom 32768 points below 150 Hz.

Options:

| Option | What it does | For | Against | Recommendation |
|---|---|---|---|---|
| L1. Multi-resolution | Bands below a crossover frequency take their values from a longer FFT; blended over about one octave around the crossover | Separate bass notes instead of one hill; the rest of the spectrum is unchanged; analysis stays around 1 s per song | Bass lines react a little earlier and fall a little later (the window is centered, so sync on average is kept, but a kick spreads over 6 frames instead of 3 at 16384); needs level matching | **Recommended**, as opt-in keys |
| L2. Different frequency axis (for example mel, or linear below a corner frequency) | Gives the bass less of the screen width | The hill gets narrow; no time smearing | Bass detail gets fewer lines; changes the whole look, which the owner liked across the full width | Optional extra, only if wanted |
| L3. Narrower window (Hann instead of Blackman) | Shrinks the spread from ±3 to ±2 bins | Trivial | Small gain; more leakage between loud and quiet bands | Not recommended alone |
| L4. Leave as is | — | The settled look stays | The hill stays | — |

Two things the spike showed that the implementation must fix:

- **Level matching.** With a longer FFT, broadband content (drums, noise) reads lower per bin, so the bass region
  looks quieter (visible in the stills). The long FFT values are gain-matched to the short ones (calibrated with
  generated noise and tones).
- **Seam.** A hard switch at the crossover shows a step; the two analyses are cross-faded over about one octave.

Proposed keys, off by default:

```toml
[analysis]
low_fft_size = 0               # 0 = off; for example 16384: a longer FFT for the low bands
low_crossover_frequency = 250.0  # Hz; blended over about one octave around it
```

Whether the `default` preset should adopt it is the owner's call after seeing stills and a clip (要確認 Q1). Adopting
it changes the settled default look, so it would get its own ADR and an intentional change of the reference hashes.

### 3. Fill colors

```toml
[fill]
mode = "solid"                 # "solid" (uses foreground), "frequency" (left to right), "height" (baseline to tip)
colors = ["#FFFFFF", "#FF00C8"]  # two or more stops, evenly spaced
```

- Drawn with a Skia gradient shader; the cost is about 1 ms per frame (spike: 17.0 → 17.9 ms).
- With `mirror = true`, the `height` gradient is symmetric around the baseline.
- `mode = "solid"` takes the existing code path, so old presets render the same bytes.
- Keying limits: a color close to the key color is removed with the background, and thin colored lines lose color
  in H.264 4:2:0 more visibly than white ones (Phase 0 results §6). Milestone 2 measures this with the same round trip
  as Phase 0 and documents when to use `prores4444` or wider bars.

### 4. Bar styles

```toml
[look]
style = "bars"                 # "bars" (as now) or "blocks"
block_height_px = 8.0          # blocks: height of one segment
block_gap_px = 3.0             # blocks: gap between segments
```

- `bars` is the current drawing. Thin lines and solid bars differ only in `bands` and `bar_fill`, so solid bars need
  no new code, only a preset (for example 64 bands, `bar_fill = 0.8`).
- `blocks` splits each bar into segments, counted from the baseline outward and mirrored when `mirror = true`. The
  last segment is drawn only when it is reached, as on an LED meter. Segments are just more quads, so the raster
  stays unchanged.
- Blocks suit few bands (32–96); with 512 bands the segments are too thin to read. `presets check` warns about that.

### 5. Glow

```toml
[fx]
glow_radius_px = 0.0           # 0 = off; blur radius of the halo
glow_strength = 1.0            # halo opacity multiplier
```

- Drawn by Skia while rasterizing: the shapes are drawn once with a blur mask filter (the halo) and once sharp on
  top. The halo takes the fill color or gradient. No extra dependency.
- Cost in the spike: 17 → 25 ms per 1080p frame on one core. With parallel workers the encoder stays the limit, so
  the total render time should change little (measured in milestone 2).
- Architecture §5 currently says effects are a post-processing step on the RGB frame. Drawing the halo with Skia is
  simpler and avoids separating lines from the background afterwards, so §5 is updated.
- **Keying risk.** The halo is a mix of the line color and the key color (light blue on blue back). Whether iMovie's
  keyer turns that into a soft, semi-transparent halo or into a hard edge with a blue fringe can only be checked in
  iMovie. Milestone 2 therefore starts with test clips (white and gradient glow, on blue and green, H.264 and ProRes
  4444) that the owner checks before glow is finished. If keying is poor, glow stays as a documented option for
  editors with better keyers, or is dropped (要確認 Q2).

A spike still with glow and a frequency gradient is in `work/phase2_spike/glow_sigma12_gradient1.png`.

### 6. Overrides on the command line (`--set`)

```
audio-spectrum render song.wav --preset default --set analysis.min_frequency=40 --set look.max_height=0.4
audio-spectrum render song.wav --set 'fill.colors=["#FFFFFF", "#00FFFF"]' --set fx.glow_radius_px=12
```

- Repeatable. `KEY` is a dotted preset key; `VALUE` uses TOML syntax. The result is validated like a preset file,
  so errors name the key and exit with code 2.
- Applied after `--preset` and before `--background` (which stays as a shortcut for `--set background=...`).
- One option covers the frequency range and every future key, instead of a growing list of dedicated flags. The GUI
  and embedding apps use the same mechanism through the API.

Alternatives considered: dedicated flags such as `--min-frequency` (more options to keep stable forever); presets
only, no overrides (every experiment needs a file).

### 7. Still frames for checks (`still`)

```
audio-spectrum still AUDIO --at 30 --at 61.5 [--preset ...] [--set ...] [--background ...] [--size ...] [--fps ...]
                     [--out-dir DIR] [--overwrite]
```

- Writes one PNG per time, named `<input name>_<seconds>s.png`, next to the input or in `--out-dir`, using the same
  temporary-file rule as videos. Prints the written paths on stdout.
- A still at time `t` is exactly the frame the video shows at `t` (frame `floor(t × fps)`), byte for byte. The whole
  song is analyzed so smoothing matches; that takes about a second.
- PNG encoding through Skia, so no new dependency.
- The same exit codes as `render`. No JSON progress events: a still takes a second or two.
- Replaces most uses of `bench/render_compare.py` for checking looks; the bench script stays for timing.

### 8. Built-in presets

Added as examples, each one documented in the user guide (要確認 Q4 for the exact set):

| Name | Look |
|---|---|
| `bars` | 64 solid white bars, mirrored |
| `blocks` | 48 segmented bars, not mirrored, baseline near the bottom |
| `glow` | `default` with a soft glow, marked as "check keying in your editor" |

`default` and `unity-classic` do not change in this phase unless Q1 decides otherwise.

### 9. Keying warnings

`presets check` prints warnings (not errors) when a fill or glow color is close to the background hue, when glow is
used on a key-color background, or when blocks are too thin to read. `render` and `still` do not emit warnings, so
the JSON events stay as they are.

### 10. Contract changes (all additive)

| Area | Change |
|---|---|
| CLI | New `still` command; new `--set` option on `render` and `still`. Existing options, defaults and behavior unchanged |
| JSON events | None |
| Exit codes | None; `still` uses the existing ones |
| Public API | New `render_stills(audio_path, preset, times, width, height, fps) -> list[ndarray]` and `override_preset(preset, assignments) -> Preset` |
| Preset format | New keys `analysis.low_fft_size`, `analysis.low_crossover_frequency`, `look.style`, `look.block_height_px`, `look.block_gap_px`, tables `[fill]` and `[fx]`; `schema_version` stays 1 |

The user guide (English and Japanese) is updated in the same commit as each change.

### 11. Look regression check

- Before any code change, hash the frames of `default` and `unity-classic` for a real clip in `work/` at several
  times, and for a full render of a generated signal.
- A new automated test stores the hashes of a few frames of both built-in presets rendered from a generated signal,
  so any unintended change of the default look fails the suite. (A Skia or NumPy upgrade may change those bytes; the
  test then fails on purpose and the hashes are renewed after a visual check.)
- After every milestone, the real-clip hashes are compared again and the result is stated in the commit message.

## Milestones and commits

1. **Tools and guard.** Golden-hash test, `--set` and `override_preset`, `still` and `render_stills`, user guide.
   Tests: overrides and their errors, still equals the video frame, hashes unchanged.
2. **Color and glow.** `[fill]`, `[fx]` glow, keying warnings. First, test clips for the owner's iMovie check (gate,
   Q2). Measurements: render time with glow, color round trip in H.264 and ProRes 4444. Tests: solid fill path
   unchanged, gradient direction, glow off equals no glow.
3. **Bar styles.** `blocks` style, built-in `bars`, `blocks` (and `glow` if Q2 passes) presets. Tests: segment
   geometry, mirror, partial segments.
4. **Low frequencies.** Multi-resolution analysis with level matching and cross-fade. Stills and a 30-second clip
   for the owner (Q1). Tests: tone separation, no step at the crossover, level of noise and tones matched within a
   tolerance, off equals Phase 1.
5. **Docs and version.** Architecture §2 and §5, development guide, indexes, a new ADR for draw-time effects (and for
   the default-preset decision if Q1 changes it); version 0.3.0.
6. **Acceptance.** `docs/working/PHASE2_ACCEPTANCE.md`.

Each milestone ends with a commit proposal for the owner's approval. Contract changes update the user guide (English
and Japanese) within their milestone.

## Acceptance criteria

- F10–F12 work from preset files and `--set`: gradient fill, glow, bars and blocks, frequency range, low-frequency
  resolution.
- With every new key at its default, frames of `default` and `unity-classic` are byte-identical to Phase 1 (hashes
  on a real clip and the golden-hash test).
- A still is byte-identical to the corresponding video frame.
- The sync, frame-count and CLI contract tests still pass; a full song with glow renders within its own length (N3).
- The owner has checked glow and the low-frequency option in iMovie and decided Q1 and Q2.
- Docs in English and Japanese match the delivered contract.

## Open questions (要確認)

- Q1. Low frequencies: keep the multi-resolution analysis opt-in, or make it the new `default` after seeing stills
  and a clip? Which crossover and FFT size look best (16384 below 250 Hz, or 32768 below 150 Hz)?
- Q2. Glow: how important is it? If iMovie keys it poorly, keep it as an option with a warning, or drop it?
- Q3. Blur in the app: not planned, because blurring in iMovie after keying is cleaner. Is that right for your use?
  How do you apply the blur in iMovie today?
- Q4. Built-in example presets: are `bars`, `blocks` and `glow` the right set? Any colors you already know you want?
- Q5. Extras not in the plan, cheap to add if wanted: a peak-hold cap that falls slowly above each bar; a
  `--start`/`--duration` option to render a short test clip of a song.
- Q6. Alpha output (F13): ADR-005 assumes iMovie cannot use alpha video. If the owner can confirm that with a test
  clip, glow and blur would key perfectly in an alpha-capable editor. Worth a quick check in this phase?
