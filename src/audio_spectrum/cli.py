"""Command-line interface: argument parsing and output formatting on top of the core."""

import argparse
import json
import shutil
import signal
import sys
import time
from pathlib import Path

from audio_spectrum import __version__
from audio_spectrum.encode import EncodeSettings
from audio_spectrum.errors import AudioSpectrumError, FfmpegNotFoundError, PresetError
from audio_spectrum.pipeline import RenderJob, RenderResult, render_video
from audio_spectrum.presets import (
    BLUE_BACK,
    GREEN_BACK,
    builtin_preset_names,
    builtin_preset_text,
    load_preset,
    parse_color,
)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_FFMPEG_MISSING = 3
EXIT_INTERRUPTED = 130

PROGRESS_INTERVAL_SECONDS = 0.25

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


def crf_value(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a whole number from 0 to 51, got {text!r}") from None
    if not 0 <= value <= 51:
        raise argparse.ArgumentTypeError(f"expected a whole number from 0 to 51, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audio-spectrum",
        description="Render an audio spectrum video on a chroma-key background.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")

    render = commands.add_parser("render", help="render videos from audio files")
    render.add_argument("audio", type=Path, nargs="+", help="input audio files (WAV, AIFF, FLAC, MP3, ...)")
    render.add_argument("-o", "--output", type=Path, help="output video; only with a single input")
    render.add_argument("--out-dir", type=Path, help="output folder (default: next to each input)")
    render.add_argument("--overwrite", action="store_true", help="replace existing output files")
    render.add_argument(
        "--preset", default="default", help="built-in preset name or path to a .toml preset file (default: default)"
    )
    render.add_argument("--background", type=background_color, help="blue, green or #RRGGBB (default: from the preset)")
    render.add_argument(
        "--size", type=frame_size, default=SIZES["1080p"], help="720p, 1080p, 1440p, 2160p or WxH (default: 1080p)"
    )
    render.add_argument(
        "--fps", type=float, default=30.0, help="frames per second, for example 24, 29.97 or 60 (default: 30)"
    )
    render.add_argument(
        "--codec", choices=sorted(CODECS), default="h264",
        help="h264 (small .mp4, default), prores (ProRes 422 .mov) or prores4444 (ProRes 4444 .mov, cleanest keying)",
    )
    render.add_argument(
        "--crf", type=crf_value, default=EncodeSettings.crf,
        help="H.264 quality from 0 to 51, lower is better (default: 14)",
    )
    render.add_argument("--no-audio", action="store_true", help="do not mux the source audio")
    render.add_argument("--workers", type=int, default=0, help="render processes (0: automatic)")
    render.add_argument(
        "--progress", choices=["text", "json", "none"], default="text",
        help="text on stderr (default), JSON Lines events on stdout, or nothing",
    )
    render.add_argument("--fail-fast", action="store_true", help="stop at the first file that fails")

    presets = commands.add_parser("presets", help="list, show or check presets")
    preset_commands = presets.add_subparsers(dest="preset_command", required=True)
    preset_commands.add_parser("list", help="list built-in presets")
    show = preset_commands.add_parser("show", help="print a built-in preset as TOML, to copy and edit")
    show.add_argument("name")
    check = preset_commands.add_parser("check", help="validate a preset file")
    check.add_argument("file", type=Path)
    return parser


def plan_outputs(args: argparse.Namespace, suffix: str) -> list[Path]:
    if args.output is not None:
        return [args.output]
    outputs = []
    for audio in args.audio:
        folder = args.out_dir if args.out_dir is not None else audio.parent
        outputs.append(folder / f"{audio.stem}_spectrum{suffix}")
    return outputs


def run_render(args: argparse.Namespace, reporter: "Reporter") -> int:
    if shutil.which("ffmpeg") is None:
        reporter.fatal(FfmpegNotFoundError("ffmpeg is not installed (brew install ffmpeg)"))
        return EXIT_FFMPEG_MISSING
    preset = load_preset(args.preset)
    if args.background is not None:
        preset = preset.model_copy(update={"background": args.background})
    codec, prores_profile = CODECS[args.codec]
    encode = EncodeSettings(
        codec=codec, crf=args.crf, prores_profile=prores_profile or EncodeSettings.prores_profile,
        include_audio=not args.no_audio,
    )
    outputs = plan_outputs(args, ".mp4" if codec == "h264" else ".mov")
    if args.out_dir is not None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
    width, height = args.size

    succeeded = failed = 0
    for index, (audio, output) in enumerate(zip(args.audio, outputs, strict=True), start=1):
        job = RenderJob(
            audio_path=audio, output_path=output, preset=preset, width=width, height=height, fps=args.fps,
            encode=encode, workers=args.workers, overwrite=args.overwrite,
        )
        try:
            result = render_video(job, reporter.progress_for(audio, output, index, len(outputs)))
        except FfmpegNotFoundError as error:
            reporter.fatal(error)
            return EXIT_FFMPEG_MISSING
        except AudioSpectrumError as error:
            failed += 1
            reporter.error(audio, error)
            if args.fail_fast:
                break
            continue
        succeeded += 1
        reporter.done(audio, result)
    reporter.finished(succeeded, failed)
    return EXIT_OK if failed == 0 else EXIT_FAILED


class Reporter:
    """Reports progress as human text on stderr, JSON Lines on stdout, or not at all."""

    def __init__(self, mode: str):
        self.mode = mode
        self._last_progress = 0.0
        self._progress_line_open = False

    def progress_for(self, audio: Path, output: Path, index: int, count: int):
        def progress(done: int, total: int) -> None:
            if done == 0:
                self._emit_start(audio, output, total, index, count)
                return
            now = time.monotonic()
            if done < total and now - self._last_progress < PROGRESS_INTERVAL_SECONDS:
                return
            self._last_progress = now
            if self.mode == "json":
                self._json(event="progress", input=str(audio), frame=done, frames=total)
            elif self.mode == "text":
                print(f"\r  {done}/{total} frames ({done * 100 // total}%)", end="", file=sys.stderr, flush=True)
                self._progress_line_open = True

        return progress

    def _emit_start(self, audio: Path, output: Path, total: int, index: int, count: int) -> None:
        if self.mode == "json":
            self._json(event="start", input=str(audio), output=str(output), frames=total, index=index, count=count)
        elif self.mode == "text":
            print(f"[{index}/{count}] {audio} -> {output}", file=sys.stderr)

    def done(self, audio: Path, result: RenderResult) -> None:
        if self.mode == "json":
            self._json(event="done", input=str(audio), output=str(result.output_path), seconds=round(result.seconds, 2))
        elif self.mode == "text":
            self._end_progress_line()
            print(f"  done in {result.seconds:.1f} s", file=sys.stderr)

    def error(self, audio: Path, error: AudioSpectrumError) -> None:
        if self.mode == "json":
            self._json(event="error", input=str(audio), code=error.code, message=str(error))
        else:
            self._end_progress_line()
            print(f"audio-spectrum: {error}", file=sys.stderr)

    def fatal(self, error: AudioSpectrumError) -> None:
        if self.mode == "json":
            self._json(event="error", code=error.code, message=str(error))
        print(f"audio-spectrum: {error}", file=sys.stderr)

    def finished(self, succeeded: int, failed: int) -> None:
        if self.mode == "json":
            self._json(event="finished", succeeded=succeeded, failed=failed)
        elif self.mode == "text" and succeeded + failed > 1:
            print(f"{succeeded} rendered, {failed} failed", file=sys.stderr)

    def interrupted(self) -> None:
        if self.mode == "json":
            self._json(event="interrupted")
        self._end_progress_line()
        print("audio-spectrum: interrupted", file=sys.stderr)

    def _end_progress_line(self) -> None:
        if self._progress_line_open:
            print(file=sys.stderr)
            self._progress_line_open = False

    @staticmethod
    def _json(**event: object) -> None:
        print(json.dumps(event, ensure_ascii=False), flush=True)


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
    if args.command == "render":
        check_render_arguments(parser, args)
    reporter = Reporter(getattr(args, "progress", "text"))
    previous_sigterm = signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    try:
        if args.command == "render":
            return run_render(args, reporter)
        if args.command == "presets":
            return run_presets(args)
    except PresetError as error:
        reporter.fatal(error)
        return EXIT_USAGE
    except KeyboardInterrupt:
        reporter.interrupted()
        return EXIT_INTERRUPTED
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
    parser.print_help()
    return EXIT_OK


def check_render_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.output is not None and len(args.audio) > 1:
        parser.error("-o/--output works with a single input; use --out-dir for several")
    if args.output is not None and args.out_dir is not None:
        parser.error("use either -o/--output or --out-dir, not both")
    if args.out_dir is not None:
        stems = [audio.stem for audio in args.audio]
        duplicates = sorted({stem for stem in stems if stems.count(stem) > 1})
        if duplicates:
            parser.error(f"inputs with the same name would overwrite each other in --out-dir: {', '.join(duplicates)}")


def _raise_keyboard_interrupt(signum, frame) -> None:
    raise KeyboardInterrupt
