English | [日本語](README.ja.md)

# audio-spectrum-app

Renders an audio spectrum video on a solid blue or green background from an audio file, fully offline. The video is
meant to be overlaid on a background video with a chroma key in a video editor. Frames are computed from the audio
timeline, so audio and video stay in exact sync.

**Status:** Phase 1 (MVP CLI) in progress. Rendering, batch mode, preset files and the CLI contract for other tools
work; effects and the GUI come in later phases. See the [Phase 1 plan](docs/working/PHASE1_PLAN.md).

## Quick start

```bash
brew install uv ffmpeg
uv sync
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
```

Run `uv run audio-spectrum render --help` for all options and `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, use, command reference and presets
- [Documentation index](docs/en/README.md): every doc, including architecture, requirements, decisions and phase records

## License

[MIT](LICENSE)
