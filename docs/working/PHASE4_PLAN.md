[Docs index](../en/README.md)

# Phase 4 plan: drawing the spectrum over another app's frames

Status: approved by the owner on 2026-10-31 with the recommended option B. P4-1 is open (`要確認`).

## Goal

The owner makes lyrics videos from a background image, lyrics captions and this app's spectrum, so far by stacking
layers in iMovie. A new repository, `lyrics-video-app`, will automate that and use this app as a library
(ADR-008: the core is meant to be embedded). This phase adds the one thing it needs from here: rendering the
spectrum **over frames that another app supplies**, with the same exact sync, parallel rendering, progress,
cancellation, audio and safe output as `render_video`. No lyrics logic comes into this repository.

Inputs: [Architecture](../en/ARCHITECTURE.md) §3 and §5, [Decisions](DECISIONS.md) ADR-008 and ADR-010,
[Phase 3 acceptance](PHASE3_ACCEPTANCE.md).

## What the lyrics app needs

Its frame `n` is: the background image, the lyrics caption of time `n / fps` (fading in and out over about 2 s) and
credits, with the spectrum drawn on top, as in today's iMovie stacking. Measured on the M1 at 1080p:

| Step | Time per frame |
|---|---|
| Drawing the spectrum (`glow` preset) | about 20 ms |
| Blending a transparent spectrum frame over a background in NumPy | about 46 ms |

Blending in the main process would make a 4-minute song several minutes slower, and the internal renderer cannot be
sent to worker processes. Drawing the spectrum directly onto the other app's frame, inside the existing workers,
avoids both.

## Options

| Option | What it is | For | Against | Recommendation |
|---|---|---|---|---|
| A. Building blocks | Make the analysis, a frame painter and `VideoWriter` public; the lyrics app writes its own render loop | Most freedom | The lyrics app re-implements parallel rendering, progress, cancellation, audio muxing, ranges and safe output, and the sync invariant lives in two places | Not recommended alone |
| B. A backdrop for `render_video` | `RenderJob.backdrop`: an object the workers ask for the picture under the spectrum at frame `n`; everything else stays as it is | One render path for both apps; sync, workers, progress, cancel, `--start`/`--duration`, audio and safe output come for free; the lyrics logic stays in the lyrics app | Only a layer under the spectrum; the backdrop object must be picklable (it is sent to the workers) | **Recommended** |
| C. Layers inside this app | Background images and captions as features of this app | No second repository | Lyrics logic in the spectrum app; against ADR-008 and the owner's wish to keep it embeddable | Not recommended |

## Design (option B)

### 1. The backdrop

```python
class Backdrop(Protocol):
    def frame(self, index: int, seconds: float, width: int, height: int) -> np.ndarray:
        """The RGB picture (height, width, 3, uint8) under the spectrum at frame `index` (time `seconds`)."""
```

- `RenderJob(..., backdrop=my_backdrop)`. Frame `n` of the full song gets `index = n` and `seconds = n / fps`, also
  for a part of a song (`start`/`duration`), so captions keep their timing.
- The spectrum is drawn over the backdrop instead of over the preset's background color. A backdrop and a
  transparent background (`EncodeSettings.alpha`) together raise `ValueError`.
- The object is sent once to every worker process, so it must be picklable (a small class holding paths and
  settings, which loads its images lazily in the worker). Exceptions in it surface as a new `BackdropError` (code
  `backdrop_failed`), and the render leaves no file, as for every other failure.
- `render_stills` and `Preview.frames` accept the same `backdrop`, so the lyrics app's previews
  are the same frames as its videos.

### 2. Drawing over a frame

The raster backend gains "draw over these pixels" next to "clear to a color". Drawing over a backdrop filled with the
preset's background color gives byte-identical frames to today's, which the tests check, so `default`, the golden
hashes and the CLI do not change.

### 3. Contract changes (all additive)

| Area | Change |
|---|---|
| Public API | `RenderJob.backdrop`, the `Backdrop` protocol, `BackdropError`; `backdrop` on `render_stills` and `Preview.frames` |
| JSON events | Error code `backdrop_failed` (only from the API; the CLI has no backdrop option) |
| CLI, presets, GUI | None |

A CLI option for a still background image is easy to add on top but is not planned: the lyrics app owns that. (要確認
P4-2)

### 4. Version and release

Version 0.5.0. The lyrics app first depends on this repository by path (`../audio-spectrum-app`, editable) while
both change; once this phase is accepted it can pin a Git tag such as `v0.5.0`. Creating and pushing the tag is the
owner's (要確認 P4-1).

## Milestones and commits

1. **Backdrop.** Drawing over supplied pixels, `RenderJob.backdrop`, `Backdrop`, `BackdropError`, stills and
   previews with a backdrop. Tests: a solid backdrop equals today's frames byte for byte; parallel equals single
   process; click-track sync with a backdrop that changes per frame (its index and seconds match the audio); a range
   passes full-song indexes; a failing backdrop leaves no file; backdrop with alpha is refused. An example backdrop
   (a still image under the spectrum) in the user guide.
2. **Docs, ADR-013, version 0.5.0** in English, Japanese and Spanish.
3. **Acceptance.** `docs/working/PHASE4_ACCEPTANCE.md`, including a timing check: a 4-minute song with an image
   backdrop still renders well within its own length.

Each milestone ends with a commit proposal for the owner's approval.

## Acceptance criteria

- With no backdrop, every output is unchanged (golden hashes, sync, CLI and GUI tests).
- A backdrop's frames reach the video in sync with the audio, for whole songs and parts, in one or many processes.
- A failing backdrop leaves no output or temporary file.
- A 4-minute song with a still-image backdrop renders in less than its own length at 1080p30 (N3).

## Decisions on open questions

Answered by the owner on 2026-10-31 ("approved with the recommended options").

- P4-1. Tagging: open, `要確認`. Until it is decided, lyrics-video-app uses the path dependency.
- P4-2. No CLI option for a background image; the lyrics app owns that.
- P4-3. Only the layer under the spectrum in this phase; an overlay hook can follow if a need appears.
