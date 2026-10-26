# Project instructions for Claude Code

## Product
audio-spectrum-app renders audio spectrum videos on a solid chroma-key background (blue or green) from an audio file,
fully offline on the owner's Mac. The videos are overlaid on separately made background videos in a video editor
(currently iMovie). It replaces a legacy Unity project that recorded the spectrum in real time.

## Read first
Before changing code or docs, read:
- [docs/en/README.md](docs/en/README.md) (docs index)
- [docs/en/ARCHITECTURE.md](docs/en/ARCHITECTURE.md) (§3 lists the invariants to keep)
- [docs/working/REQUIREMENTS.md](docs/working/REQUIREMENTS.md)
- [docs/working/DECISIONS.md](docs/working/DECISIONS.md)
- The current phase plan in `docs/working/` (`PHASE<N>_PLAN.md`)

If any path does not exist, report it rather than silently inventing its contents.

## Project principles
- Frame `n` always shows the audio at time `n / fps`. Never render by playing audio in real time; audio and video must
  not drift.
- Songs, rendered videos and reference frames never enter the repository. Keep them in the ignored `work/` directory
  or outside the repository.
- Normal use is fully offline: no network connection.
- Keep analysis, rendering and encoding as separate components so new styles, renderers and output formats plug in
  without reworking the rest.
- The legacy Unity project is local reference material only (see `CLAUDE.local.md` if present). Never commit it or
  name its folder in tracked files.

## Engineering
- Python 3.13 managed with `uv`; ffmpeg is an external tool (`brew install ffmpeg`).
- Tests: `uv run pytest`. Automated tests use generated signals only, never real songs. More:
  [Development](docs/en/DEVELOPMENT.md).
- The CLI options, JSON events, exit codes and the names exported by `audio_spectrum` are a public contract for
  embedding apps ([User guide](docs/en/USER_GUIDE.md) §5). Change them only deliberately and update the guide.

## Workflow
- Work in phases: write a plan in `docs/working/PHASE<N>_PLAN.md`, get the owner's approval, then implement, measure and
  propose a commit per milestone. Each phase ends with a report in `docs/working/` (`PHASE0_RESULTS.md`, then
  `PHASE<N>_ACCEPTANCE.md`).
- Work and commit on the `dev` branch, which the owner created after the first push.

## Overrides of shared rules
None.
