"""Backdrops: pictures under the spectrum supplied by an embedding app, frame by frame."""

import shutil
import subprocess

import numpy as np
import pytest
import skia
import soundfile as sf

from audio_spectrum import (
    BackdropError,
    EncodeSettings,
    RenderJob,
    encode_png,
    load_preset,
    render_stills,
    render_video,
)
from audio_spectrum.analysis import analyze
from audio_spectrum.audio import load_audio
from audio_spectrum.pipeline import _frames
from signals import SAMPLE_RATE, sine

WIDTH, HEIGHT = 320, 180
FPS = 30
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


class Solid:
    """One color everywhere."""

    def __init__(self, color):
        self.color = color

    def frame(self, index, seconds, width, height):
        picture = np.empty((height, width, 3), np.uint8)
        picture[:] = self.color
        return picture


class FrameNumber:
    """Writes the frame index into the top-left corner (red = index % 256, green = index // 256), and fails loudly if
    the time does not belong to the index."""

    def frame(self, index, seconds, width, height):
        assert abs(seconds - index / FPS) < 1e-9, (index, seconds)
        picture = np.zeros((height, width, 3), np.uint8)
        picture[:20, :20] = (index % 256, index // 256, 0)
        return picture


class FailsAt:
    def __init__(self, index):
        self.index = index

    def frame(self, index, seconds, width, height):
        if index == self.index:
            raise RuntimeError("no picture")
        return np.zeros((height, width, 3), np.uint8)


class WrongSize:
    def frame(self, index, seconds, width, height):
        return np.zeros((height // 2, width, 3), np.uint8)


class StillImage:
    """The example of the user guide: one image file under the whole video, loaded once per process."""

    def __init__(self, path):
        self.path = str(path)
        self._picture = None

    def frame(self, index, seconds, width, height):
        if self._picture is None:
            image = skia.Image.open(self.path).resize(width, height)
            self._picture = image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3].copy()
        return self._picture


@pytest.fixture
def tone(tmp_path):
    path = tmp_path / "tone.wav"
    sf.write(path, sine(220, 3.0, 0.5) + sine(2000, 3.0, 0.2), SAMPLE_RATE)
    return path


def values_of(path, preset):
    return analyze(load_audio(path), FPS, preset.analysis)


@pytest.mark.parametrize("name", ["default", "glow", "blocks", "unity-classic"])
@pytest.mark.parametrize("workers", [1, 2])
def test_a_backdrop_of_the_preset_color_changes_nothing(tone, name, workers):
    preset = load_preset(name)
    values = values_of(tone, preset)
    plain = RenderJob(tone, tone, preset, WIDTH, HEIGHT, FPS, workers=workers)
    backed = RenderJob(tone, tone, preset, WIDTH, HEIGHT, FPS, workers=workers, backdrop=Solid(preset.background))
    for one, other in zip(_frames(plain, values), _frames(backed, values), strict=True):
        assert np.array_equal(one, other)


@pytest.mark.parametrize("workers", [1, 2])
def test_backdrops_get_the_index_and_time_of_every_frame(tone, workers):
    preset = load_preset("default")
    values = values_of(tone, preset)
    job = RenderJob(tone, tone, preset, WIDTH, HEIGHT, FPS, workers=workers, backdrop=FrameNumber())
    frames = list(_frames(job, values[40:70], first=40))
    assert [int(frame[5, 5, 0]) for frame in frames] == list(range(40, 70))


def test_the_spectrum_is_drawn_over_the_backdrop(tmp_path, tone):
    image_path = tmp_path / "back.png"
    picture = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    picture[:, : WIDTH // 2] = (200, 30, 30)
    picture[:, WIDTH // 2:] = (30, 200, 30)
    image_path.write_bytes(encode_png(picture))
    frame = render_stills(tone, load_preset("bars"), [1.0], WIDTH, HEIGHT, FPS, backdrop=StillImage(image_path))[0]
    assert tuple(frame[2, 2]) == (200, 30, 30) and tuple(frame[2, -3]) == (30, 200, 30)
    assert np.any(np.all(frame == (255, 255, 255), axis=2))


def test_stills_with_a_backdrop_equal_the_video_frames(tone):
    preset = load_preset("glow")
    values = values_of(tone, preset)
    job = RenderJob(tone, tone, preset, WIDTH, HEIGHT, FPS, workers=2, backdrop=FrameNumber())
    video = list(_frames(job, values))
    stills = render_stills(tone, preset, [0.0, 1.0, 2.5], WIDTH, HEIGHT, FPS, backdrop=FrameNumber())
    for still, index in zip(stills, [0, 30, 75], strict=True):
        assert np.array_equal(still, video[index])


@needs_ffmpeg
def test_a_part_of_the_song_passes_whole_song_frame_numbers(tone, tmp_path):
    output = tmp_path / "part.mov"
    job = RenderJob(
        tone, output, load_preset("default"), WIDTH, HEIGHT, FPS, EncodeSettings(codec="prores", prores_profile=4),
        workers=2, start=1.0, duration=0.5, backdrop=FrameNumber(),
    )
    assert render_video(job).frames == 15
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    frames = np.frombuffer(decoded, np.uint8).reshape(-1, HEIGHT, WIDTH, 3)
    assert [int(frame[5, 5, 0]) for frame in frames] == list(range(30, 45))


@needs_ffmpeg
@pytest.mark.parametrize("workers", [1, 2])
@pytest.mark.parametrize("backdrop", [FailsAt(20), WrongSize()], ids=["raises", "wrong size"])
def test_a_failing_backdrop_leaves_no_file(tone, tmp_path, workers, backdrop):
    output = tmp_path / "out.mp4"
    job = RenderJob(tone, output, load_preset("default"), WIDTH, HEIGHT, FPS, workers=workers, backdrop=backdrop)
    with pytest.raises(BackdropError) as caught:
        render_video(job)
    assert caught.value.code == "backdrop_failed"
    assert "frame" in str(caught.value)
    assert [path.name for path in tmp_path.iterdir()] == ["tone.wav"]


def test_a_backdrop_cannot_be_combined_with_a_transparent_background(tone):
    with pytest.raises(ValueError, match="backdrop"):
        RenderJob(tone, tone, load_preset("default"), encode=EncodeSettings(codec="prores", prores_profile=4,
                                                                             alpha=True), backdrop=Solid((0, 0, 0)))
    with pytest.raises(ValueError, match="transparent"):
        render_stills(tone, load_preset("default"), [1.0], WIDTH, HEIGHT, FPS, transparent=True,
                      backdrop=Solid((0, 0, 0)))
