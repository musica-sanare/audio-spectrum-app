English | [日本語](README.ja.md) | [Español](README.es.md)

# audio-spectrum-app

Renders an audio spectrum video on a solid blue or green background from an audio file, fully offline. The video is
meant to be overlaid on a background video with a chroma key in a video editor. Frames are computed from the audio
timeline, so audio and video stay in exact sync.

**Status:** Phase 3 (GUI) implemented, version 0.4.0; Phases 2 and 3 await acceptance. The CLI renders with
effects and styles (gradients, glow, bars and blocks, sharper bass, transparent ProRes 4444); `audio-spectrum gui`
opens a local web page in Japanese, English or Spanish to adjust the look with previews, render, and save presets.
See the acceptance reports for [Phase 2](docs/working/PHASE2_ACCEPTANCE.md) and
[Phase 3](docs/working/PHASE3_ACCEPTANCE.md) (both drafts).

## Quick start

```bash
brew install uv ffmpeg
uv sync
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
uv run audio-spectrum gui                                   # the same in a local web page, with previews
```

Run `uv run audio-spectrum render --help` for all options and `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, use, command reference and presets
- [Documentation index](docs/en/README.md): every doc, including architecture, requirements, decisions and phase records

## License

[MIT](LICENSE)
