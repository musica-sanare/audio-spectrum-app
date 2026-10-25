"""Errors raised by the core. The CLI maps each type to an exit code."""


class AudioSpectrumError(Exception):
    """Base class for errors the core reports to callers."""


class PresetError(AudioSpectrumError):
    """A preset name is unknown, or a preset file cannot be read or is invalid."""
