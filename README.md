English | [日本語](README.ja.md)

# audio-spectrum-app

Renders an audio spectrum video on a solid blue or green background from an audio file, fully offline. The video is
meant to be overlaid on a background video with a chroma key in a video editor. Frames are computed from the audio
timeline, so audio and video stay in exact sync.

**Status:** Phase 0 (foundation and spike) complete. A working `render` command exists; presets, batch mode and the
GUI come in later phases. See [Phase 0 results](docs/working/PHASE0_RESULTS.md).

## Quick start

```bash
brew install uv ffmpeg
uv sync
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
```

Run `uv run audio-spectrum render --help` for all options and `uv run pytest` for the tests.

## Documentation

- [Documentation index](docs/en/README.md): every doc, including requirements, decisions and phase records

## License

[MIT](LICENSE)
