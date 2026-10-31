English | [日本語](README.ja.md) | [Español](README.es.md)

# audio-spectrum-app

Renders an audio spectrum video on a solid blue or green background from an audio file, fully offline. The video is
meant to be overlaid on a background video with a chroma key in a video editor. Frames are computed from the audio
timeline, so audio and video stay in exact sync.

## Status

Phases 1 to 4 are accepted; the current version is 0.5.0.

- **CLI:** renders with effects and styles: gradients, glow, bars and blocks, sharper bass, transparent ProRes 4444.
- **GUI:** `audio-spectrum gui` opens a local web page in Japanese, English or Spanish. It adjusts the look with
  previews, renders, and saves presets.
- **Embedding:** other apps can draw the spectrum over their own frames.

Details are in the acceptance reports for [Phase 2](docs/working/PHASE2_ACCEPTANCE.md),
[Phase 3](docs/working/PHASE3_ACCEPTANCE.md) and [Phase 4](docs/working/PHASE4_ACCEPTANCE.md).

## Quick start

```bash
brew install uv ffmpeg
```

```bash
uv sync
```

```bash
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
uv run audio-spectrum gui                                   # the same in a local web page, with previews
```

Run `uv run audio-spectrum render --help` for all options and `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, everyday use, the GUI, presets and command reference
- [Embedding guide](docs/en/EMBEDDING.md): use from scripts and other apps (JSON events, Python API)
- [Documentation index](docs/en/README.md): every doc, including architecture, requirements, decisions and phase records

## License

[MIT](LICENSE)
