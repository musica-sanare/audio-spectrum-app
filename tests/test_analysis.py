import numpy as np
import pytest

from audio_spectrum.analysis import AnalysisSettings, analyze, frame_count
from signals import SAMPLE_RATE, sine, stereo

UNSMOOTHED = AnalysisSettings(attack_seconds=0, release_seconds=0)


def band_edges(settings: AnalysisSettings) -> np.ndarray:
    return np.geomspace(settings.min_frequency, settings.max_frequency, settings.num_bands + 1)


@pytest.mark.parametrize(
    ("num_samples", "sample_rate", "fps", "expected"),
    [(48000, 48000, 30, 30), (48001, 48000, 30, 31), (96000, 48000, 60, 120), (44100 * 3, 44100, 29.97, 90)],
)
def test_frame_count_covers_the_whole_audio(num_samples, sample_rate, fps, expected):
    assert frame_count(num_samples, sample_rate, fps) == expected


def test_one_row_per_frame_and_values_in_range():
    values = analyze(stereo(sine(1000, 2.0)), fps=30)
    assert values.shape == (60, 128)
    assert values.dtype == np.float32
    assert 0.0 <= values.min() and values.max() <= 1.0


@pytest.mark.parametrize("frequency", [60, 440, 1000, 5000, 12000])
def test_sine_peaks_in_the_band_containing_its_frequency(frequency):
    values = analyze(stereo(sine(frequency, 1.0)), fps=30, settings=UNSMOOTHED)
    peak_band = int(values[15].argmax())
    edges = band_edges(UNSMOOTHED)
    assert edges[peak_band] <= frequency < edges[peak_band + 1] * 1.05


def test_full_scale_sine_reads_full_and_silence_reads_zero():
    loud = analyze(stereo(sine(1000, 1.0)), fps=30, settings=UNSMOOTHED)
    silent = analyze(stereo(np.zeros(SAMPLE_RATE, np.float32)), fps=30, settings=UNSMOOTHED)
    assert loud[15].max() == pytest.approx(1.0, abs=0.02)
    assert silent.max() == 0.0


def test_db_scale_maps_minus_30_db_to_half_height():
    values = analyze(stereo(sine(1000, 1.0, amplitude=10 ** (-30 / 20))), fps=30, settings=UNSMOOTHED)
    assert values[15].max() == pytest.approx(0.5, abs=0.02)


def test_frame_n_shows_the_audio_at_n_over_fps():
    fps = 30
    silence = np.zeros(SAMPLE_RATE, np.float32)
    burst = np.concatenate([silence, sine(1000, 1.0)])
    values = analyze(stereo(burst), fps=fps, settings=UNSMOOTHED).max(axis=1)
    onset_frame = fps  # the tone starts at 1.0 s
    window_frames = UNSMOOTHED.fft_size / SAMPLE_RATE * fps / 2
    assert values[: onset_frame - int(np.ceil(window_frames))].max() == 0.0
    assert values[onset_frame] > 0.5
    assert values[onset_frame + int(np.ceil(window_frames)):].min() > 0.95


def test_channel_setting_selects_the_analyzed_signal():
    audio = stereo(sine(1000, 1.0), np.zeros(SAMPLE_RATE, np.float32))
    left = AnalysisSettings(channel="left", attack_seconds=0, release_seconds=0)
    right = AnalysisSettings(channel="right", attack_seconds=0, release_seconds=0)
    assert analyze(audio, fps=30, settings=left).max() == pytest.approx(1.0, abs=0.02)
    assert analyze(audio, fps=30, settings=right).max() == 0.0
    # The mix halves a one-sided signal: -6 dB, 0.9 on the 60 dB scale.
    assert analyze(audio, fps=30, settings=UNSMOOTHED).max() == pytest.approx(0.9, abs=0.02)


def test_release_makes_values_fall_gradually_and_attack_rise_quickly():
    tone_then_silence = np.concatenate([sine(1000, 1.0), np.zeros(SAMPLE_RATE, np.float32)])
    settings = AnalysisSettings(attack_seconds=0.01, release_seconds=0.3)
    values = analyze(stereo(tone_then_silence), fps=30, settings=settings).max(axis=1)
    assert values[10] > 0.95
    after_stop = values[33:45]
    assert np.all(np.diff(after_stop) < 0)
    assert after_stop[0] > 0.5


def test_linear_scale_spreads_bands_evenly():
    settings = AnalysisSettings(
        frequency_scale="linear", magnitude_scale="linear", min_frequency=0, max_frequency=24000,
        num_bands=2048, channel="left", attack_seconds=0, release_seconds=0,
    )
    values = analyze(stereo(sine(3000, 1.0)), fps=30, settings=settings)
    assert int(values[15].argmax()) == 3000 * 2048 // 24000


def test_analysis_is_deterministic():
    audio = stereo(sine(440, 1.0) + sine(3000, 1.0, amplitude=0.3))
    assert np.array_equal(analyze(audio, fps=30), analyze(audio, fps=30))


def test_tilt_boosts_highs_and_cuts_lows_around_1_khz():
    tilted = AnalysisSettings(tilt_db_per_octave=6.0, attack_seconds=0, release_seconds=0)
    half_scale = 10 ** (-12 / 20)

    def peak(frequency):
        return analyze(stereo(sine(frequency, 1.0, amplitude=half_scale)), fps=30, settings=tilted)[15].max()

    one_octave_in_db = 6.0 / -tilted.db_floor
    assert peak(2000) - peak(1000) == pytest.approx(one_octave_in_db, abs=0.01)
    assert peak(1000) - peak(500) == pytest.approx(one_octave_in_db, abs=0.01)
