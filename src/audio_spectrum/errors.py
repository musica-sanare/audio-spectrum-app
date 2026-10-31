"""Errors raised by the core. The CLI maps each type to an exit code and an error code in JSON progress."""


class AudioSpectrumError(Exception):
    """Base class for errors the core reports to callers."""

    code = "error"


class PresetError(AudioSpectrumError):
    """A preset name is unknown, or a preset file cannot be read or is invalid."""

    code = "preset_invalid"


class DecodeError(AudioSpectrumError):
    """An input audio file is missing or cannot be decoded."""

    code = "decode_failed"


class EncodeError(AudioSpectrumError):
    """ffmpeg failed while writing the video."""

    code = "encode_failed"


class WorkerError(AudioSpectrumError):
    """A render worker process died."""

    code = "worker_failed"


class OutputExistsError(AudioSpectrumError):
    """The output file exists and overwriting was not allowed."""

    code = "output_exists"


class FfmpegNotFoundError(AudioSpectrumError):
    """ffmpeg is not installed or not on PATH."""

    code = "ffmpeg_not_found"


class Cancelled(AudioSpectrumError):
    """The caller cancelled the render."""

    code = "cancelled"


class TimeRangeError(AudioSpectrumError):
    """A still was requested at a time outside the audio."""

    code = "time_out_of_range"


class BackdropError(AudioSpectrumError):
    """The backdrop given to a render failed or returned a picture of the wrong size or type."""

    code = "backdrop_failed"
