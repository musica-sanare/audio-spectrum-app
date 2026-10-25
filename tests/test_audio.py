import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf

from audio_spectrum.audio import Audio, load_audio
from audio_spectrum.errors import DecodeError
from signals import SAMPLE_RATE, sine, stereo


def test_load_wav_keeps_samples_and_rate(tmp_path):
    path = tmp_path / "tone.wav"
    sf.write(path, sine(440, 0.5, amplitude=0.5), SAMPLE_RATE, subtype="FLOAT")
    audio = load_audio(path)
    assert audio.sample_rate == SAMPLE_RATE
    assert audio.samples.shape == (SAMPLE_RATE // 2, 1)
    assert audio.duration == pytest.approx(0.5)


def test_channel_modes():
    audio = stereo(np.ones(10, dtype=np.float32), np.zeros(10, dtype=np.float32))
    assert audio.channel("left").tolist() == [1.0] * 10
    assert audio.channel("right").tolist() == [0.0] * 10
    assert audio.channel("mix").tolist() == [0.5] * 10


def test_right_channel_of_mono_falls_back_to_the_only_channel():
    audio = Audio(samples=np.ones((4, 1), np.float32), sample_rate=1)
    assert audio.channel("right").tolist() == [1.0] * 4


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_formats_libsndfile_cannot_read_are_decoded_with_ffmpeg(tmp_path):
    wav = tmp_path / "tone.wav"
    m4a = tmp_path / "tone.m4a"
    sf.write(wav, sine(440, 1.0, amplitude=0.5), SAMPLE_RATE)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), str(m4a)], check=True)
    audio = load_audio(m4a)
    assert audio.samples.shape[1] == 2
    assert audio.duration == pytest.approx(1.0, abs=0.05)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_mp3_input_is_decoded(tmp_path):
    wav = tmp_path / "tone.wav"
    mp3 = tmp_path / "tone.mp3"
    sf.write(wav, sine(440, 1.0, amplitude=0.5), SAMPLE_RATE)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), str(mp3)], check=True)
    audio = load_audio(mp3)
    assert audio.duration == pytest.approx(1.0, abs=0.06)
    assert np.abs(audio.samples).max() == pytest.approx(0.5, abs=0.05)


def test_missing_file_is_a_decode_error(tmp_path):
    with pytest.raises(DecodeError, match="file not found"):
        load_audio(tmp_path / "missing.wav")
