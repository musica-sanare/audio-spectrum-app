"""Render sample frames from a song for visual review, and time the renderer.

Usage: uv run python bench/render_compare.py SONG [--preset NAME] [--bands N ...] [--out DIR] [--times SECONDS ...]
Writes PNG files to the output directory (default: work/render_compare, ignored by Git).
"""

import argparse
import time
from pathlib import Path

import numpy as np
import skia

from audio_spectrum.analysis import analyze
from audio_spectrum.audio import Audio, load_audio
from audio_spectrum.presets import Preset, load_preset
from audio_spectrum.renderer import FrameRenderer

FPS = 30
TIMED_FRAMES = 300


def save_png(frame: np.ndarray, path: Path) -> None:
    rgba = np.dstack([frame, np.full(frame.shape[:2], 255, np.uint8)])
    skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType).save(str(path), skia.kPNG)


def render_samples(preset: Preset, audio: Audio, times: list[float], size: tuple[int, int], out: Path, label: str):
    values = analyze(audio, FPS, preset.analysis)
    renderer = FrameRenderer(preset, *size)
    for seconds in times:
        frame = renderer.render(values[min(round(seconds * FPS), len(values) - 1)])
        save_png(frame, out / f"{label}_{size[0]}x{size[1]}_{seconds:g}s.png")
    start = len(values) // 3
    started = time.perf_counter()
    for row in values[start:start + TIMED_FRAMES]:
        renderer.render(row)
    per_frame = (time.perf_counter() - started) / TIMED_FRAMES
    print(f"{label}: {per_frame * 1000:.1f} ms/frame ({1 / per_frame:.0f} fps)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("song", type=Path)
    parser.add_argument("--preset", default="default", help="built-in preset name or .toml path")
    parser.add_argument("--bands", type=int, nargs="*", default=[], help="also render the preset with these band counts")
    parser.add_argument("--out", type=Path, default=Path("work/render_compare"))
    parser.add_argument("--times", type=float, nargs="+", default=[30.0, 60.0, 90.0])
    parser.add_argument("--size", default="1920x1080")
    args = parser.parse_args()
    size = tuple(int(n) for n in args.size.split("x"))
    args.out.mkdir(parents=True, exist_ok=True)
    audio = load_audio(args.song)

    preset = load_preset(args.preset)
    render_samples(preset, audio, args.times, size, args.out, preset.name)
    for bands in args.bands:
        variant = preset.model_copy(update={"analysis": preset.analysis.model_copy(update={"bands": bands})})
        render_samples(variant, audio, args.times, size, args.out, f"{preset.name}-{bands}bands")


if __name__ == "__main__":
    main()
