import argparse
import dataclasses
import sys
import time
from pathlib import Path

from audio_spectrum import __version__
from audio_spectrum.encode import EncodeSettings
from audio_spectrum.pipeline import RenderJob, render_video
from audio_spectrum.presets import BLUE_BACK, GREEN_BACK, PRESETS, Color

NAMED_BACKGROUNDS: dict[str, Color] = {"blue": BLUE_BACK, "green": GREEN_BACK}
CODECS = {"h264": ("h264", 0), "prores": ("prores", 2), "prores4444": ("prores", 4)}
SIZES = {"720p": (1280, 720), "1080p": (1920, 1080), "1440p": (2560, 1440), "2160p": (3840, 2160)}


def parse_color(text: str) -> Color:
    if text in NAMED_BACKGROUNDS:
        return NAMED_BACKGROUNDS[text]
    digits = text.removeprefix("#")
    if len(digits) != 6:
        raise argparse.ArgumentTypeError(f"expected blue, green or #RRGGBB, got {text!r}")
    try:
        return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected blue, green or #RRGGBB, got {text!r}") from None


def parse_size(text: str) -> tuple[int, int]:
    if text in SIZES:
        return SIZES[text]
    try:
        width, height = (int(part) for part in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected 1080p or WIDTHxHEIGHT, got {text!r}") from None
    if width % 2 or height % 2:
        raise argparse.ArgumentTypeError("width and height must be even")
    return width, height


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audio-spectrum",
        description="Render an audio spectrum video on a chroma-key background.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")

    render = commands.add_parser("render", help="render a video from an audio file")
    render.add_argument("audio", type=Path, help="input audio file (WAV, AIFF, FLAC, MP3, ...)")
    render.add_argument("-o", "--output", type=Path, help="output video (default: next to the input, .mp4 or .mov)")
    render.add_argument("--preset", default="default", choices=sorted(PRESETS))
    render.add_argument("--background", type=parse_color, help="blue, green or #RRGGBB (default: from the preset)")
    render.add_argument("--size", type=parse_size, default=SIZES["1080p"], help="720p, 1080p, 1440p, 2160p or WxH")
    render.add_argument("--fps", type=float, default=30.0)
    render.add_argument(
        "--codec", choices=sorted(CODECS), default="h264",
        help="h264 (small .mp4), prores (ProRes 422 .mov) or prores4444 (ProRes 4444 .mov, cleanest keying)",
    )
    render.add_argument("--crf", type=int, default=EncodeSettings.crf, help="H.264 quality (lower is better)")
    render.add_argument("--no-audio", action="store_true", help="do not mux the source audio")
    render.add_argument("--workers", type=int, default=0, help="render processes (0: automatic)")
    return parser


def run_render(args: argparse.Namespace) -> int:
    preset = PRESETS[args.preset]
    if args.background is not None:
        preset = dataclasses.replace(preset, background=args.background)
    codec, prores_profile = CODECS[args.codec]
    suffix = ".mp4" if codec == "h264" else ".mov"
    output = args.output or args.audio.with_name(f"{args.audio.stem}_spectrum{suffix}")
    width, height = args.size
    job = RenderJob(
        audio_path=args.audio,
        output_path=output,
        preset=preset,
        width=width,
        height=height,
        fps=args.fps,
        encode=EncodeSettings(
            codec=codec, crf=args.crf, prores_profile=prores_profile or EncodeSettings.prores_profile,
            include_audio=not args.no_audio,
        ),
        workers=args.workers,
    )
    started = time.perf_counter()

    def progress(done: int, total: int) -> None:
        if done == total or done % 100 == 0:
            print(f"\r{done}/{total} frames", end="", file=sys.stderr, flush=True)

    frames = render_video(job, progress)
    print(f"\nWrote {output} ({frames} frames in {time.perf_counter() - started:.1f} s)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "render":
        return run_render(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
