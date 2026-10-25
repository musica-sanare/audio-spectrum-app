"""Command-line interface: argument parsing and output formatting on top of the core."""

import argparse
import sys
import time
from pathlib import Path

from audio_spectrum import __version__
from audio_spectrum.encode import EncodeSettings
from audio_spectrum.errors import PresetError
from audio_spectrum.pipeline import RenderJob, render_video
from audio_spectrum.presets import (
    BLUE_BACK,
    GREEN_BACK,
    builtin_preset_names,
    builtin_preset_text,
    load_preset,
    parse_color,
)

EXIT_OK = 0
EXIT_USAGE = 2

NAMED_BACKGROUNDS = {"blue": BLUE_BACK, "green": GREEN_BACK}
CODECS = {"h264": ("h264", 0), "prores": ("prores", 2), "prores4444": ("prores", 4)}
SIZES = {"720p": (1280, 720), "1080p": (1920, 1080), "1440p": (2560, 1440), "2160p": (3840, 2160)}


def background_color(text: str) -> tuple[int, int, int]:
    if text in NAMED_BACKGROUNDS:
        return NAMED_BACKGROUNDS[text]
    try:
        return parse_color(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected blue, green or #RRGGBB, got {text!r}") from None


def frame_size(text: str) -> tuple[int, int]:
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
    render.add_argument("--preset", default="default", help="built-in preset name or path to a .toml preset file")
    render.add_argument("--background", type=background_color, help="blue, green or #RRGGBB (default: from the preset)")
    render.add_argument("--size", type=frame_size, default=SIZES["1080p"], help="720p, 1080p, 1440p, 2160p or WxH")
    render.add_argument("--fps", type=float, default=30.0)
    render.add_argument(
        "--codec", choices=sorted(CODECS), default="h264",
        help="h264 (small .mp4), prores (ProRes 422 .mov) or prores4444 (ProRes 4444 .mov, cleanest keying)",
    )
    render.add_argument("--crf", type=int, default=EncodeSettings.crf, help="H.264 quality (lower is better)")
    render.add_argument("--no-audio", action="store_true", help="do not mux the source audio")
    render.add_argument("--workers", type=int, default=0, help="render processes (0: automatic)")

    presets = commands.add_parser("presets", help="list, show or check presets")
    preset_commands = presets.add_subparsers(dest="preset_command", required=True)
    preset_commands.add_parser("list", help="list built-in presets")
    show = preset_commands.add_parser("show", help="print a built-in preset as TOML, to copy and edit")
    show.add_argument("name")
    check = preset_commands.add_parser("check", help="validate a preset file")
    check.add_argument("file", type=Path)
    return parser


def run_render(args: argparse.Namespace) -> int:
    preset = load_preset(args.preset)
    if args.background is not None:
        preset = preset.model_copy(update={"background": args.background})
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
    return EXIT_OK


def run_presets(args: argparse.Namespace) -> int:
    if args.preset_command == "list":
        for name in builtin_preset_names():
            print(name)
    elif args.preset_command == "show":
        print(builtin_preset_text(args.name), end="")
    else:
        preset = load_preset(args.file)
        print(f"{args.file}: valid preset {preset.name!r}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            return run_render(args)
        if args.command == "presets":
            return run_presets(args)
    except PresetError as error:
        print(f"audio-spectrum: {error}", file=sys.stderr)
        return EXIT_USAGE
    parser.print_help()
    return EXIT_OK
