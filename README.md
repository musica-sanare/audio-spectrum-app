English | [日本語](README.ja.md)

# audio-spectrum-app

Renders an audio spectrum video on a solid blue or green background from an audio file, fully offline. The video is
meant to be overlaid on a background video with a chroma key in a video editor. Frames are computed from the audio
timeline, so audio and video stay in exact sync.

**Status:** Phase 0 (foundation and spike) in progress. Not usable yet. See the
[Phase 0 plan](docs/working/PHASE0_PLAN.md).

## Quick start

```bash
brew install uv ffmpeg
uv sync
uv run pytest
```

## Documentation

- [Documentation index](docs/en/README.md): every doc, including requirements, decisions and phase records

## License

[MIT](LICENSE)
