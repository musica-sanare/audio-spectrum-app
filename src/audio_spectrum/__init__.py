"""Render audio spectrum videos on a chroma-key background.

Public API: the names in `__all__`. Everything else is internal and may change without notice.

    from audio_spectrum import RenderJob, load_preset, render_video

    if __name__ == "__main__":  # required: render workers re-import the main script
        job = RenderJob(Path("song.wav"), Path("song_spectrum.mp4"), load_preset("default"))
        result = render_video(job)
"""

__version__ = "0.4.0"

from audio_spectrum.encode import EncodeSettings, encode_png
from audio_spectrum.errors import (
    AudioSpectrumError,
    BackdropError,
    Cancelled,
    DecodeError,
    EncodeError,
    FfmpegNotFoundError,
    OutputExistsError,
    PresetError,
    TimeRangeError,
    WorkerError,
)
from audio_spectrum.pipeline import Backdrop, Preview, RenderJob, RenderResult, render_stills, render_video
from audio_spectrum.presets import (
    Preset,
    builtin_preset_names,
    load_preset,
    override_preset,
    preset_schema,
    preset_to_toml,
    preset_warnings,
    save_user_preset,
    shadowed_user_preset_names,
    user_preset_folder,
    user_preset_names,
)

__all__ = [
    "AudioSpectrumError",
    "Backdrop",
    "BackdropError",
    "Cancelled",
    "DecodeError",
    "EncodeError",
    "EncodeSettings",
    "FfmpegNotFoundError",
    "OutputExistsError",
    "Preset",
    "PresetError",
    "Preview",
    "RenderJob",
    "RenderResult",
    "TimeRangeError",
    "WorkerError",
    "__version__",
    "builtin_preset_names",
    "encode_png",
    "load_preset",
    "override_preset",
    "preset_schema",
    "preset_to_toml",
    "preset_warnings",
    "render_stills",
    "render_video",
    "save_user_preset",
    "shadowed_user_preset_names",
    "user_preset_folder",
    "user_preset_names",
]
