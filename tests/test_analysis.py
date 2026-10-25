import numpy as np
import pytest

from audio_spectrum.analysis import AnalysisSettings, analyze, frame_count
from signals import SAMPLE_RATE, sine, stereo

BASE = dict(bands=128, db_floor=-60.0, tilt_db_per_octave=0.0)
UNSMOOTHED = AnalysisSettings(**BASE, attack_seconds=0, release_seconds=0)


def band_edges(settings: AnalysisSettings) -> np.ndarray:
    return np.geomspace(settings.min_frequency, settings.max_frequency, settings.bands + 1)


@pytest.mark.parametrize(
    ("num_samples", "sample_rate", "fps", "expected"),
    [(48000, 48000, 30, 30), (48001, 48000, 30, 31), (96000, 48000, 60, 120), (44100 * 3, 44100, 29.97, 90)],
)
def test_frame_count_covers_the_whole_audio(num_samples, sample_rate, fps, expected):
    assert frame_count(num_samples, sample_rate, fps) == expected


def test_one_row_per_frame_and_values_in_range():
    values = analyze(stereo(sine(1000, 2.0)), fps=30, settings=AnalysisSettings(**BASE))
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
    left = AnalysisSettings(**BASE, channel="left", attack_seconds=0, release_seconds=0)
    right = AnalysisSettings(**BASE, channel="right", attack_seconds=0, release_seconds=0)
    assert analyze(audio, fps=30, settings=left).max() == pytest.approx(1.0, abs=0.02)
    assert analyze(audio, fps=30, settings=right).max() == 0.0
    # The mix halves a one-sided signal: -6 dB, 0.9 on the 60 dB scale.
    assert analyze(audio, fps=30, settings=UNSMOOTHED).max() == pytest.approx(0.9, abs=0.02)


def test_release_makes_values_fall_gradually_and_attack_rise_quickly():
    tone_then_silence = np.concatenate([sine(1000, 1.0), np.zeros(SAMPLE_RATE, np.float32)])
    settings = AnalysisSettings(**BASE, attack_seconds=0.01, release_seconds=0.3)
    values = analyze(stereo(tone_then_silence), fps=30, settings=settings).max(axis=1)
    assert values[10] > 0.95
    after_stop = values[33:45]
    assert np.all(np.diff(after_stop) < 0)
    assert after_stop[0] > 0.5


def test_linear_scale_spreads_bands_evenly():
    settings = AnalysisSettings(
        frequency_scale="linear", magnitude_scale="linear", min_frequency=0, max_frequency=24000,
        bands=2048, tilt_db_per_octave=0.0, channel="left", attack_seconds=0, release_seconds=0,
    )
    values = analyze(stereo(sine(3000, 1.0)), fps=30, settings=settings)
    assert int(values[15].argmax()) == 3000 * 2048 // 24000


def test_analysis_is_deterministic():
    audio = stereo(sine(440, 1.0) + sine(3000, 1.0, amplitude=0.3))
    assert np.array_equal(analyze(audio, fps=30), analyze(audio, fps=30))


def test_tilt_boosts_highs_and_cuts_lows_around_1_khz():
    tilted = AnalysisSettings(bands=128, db_floor=-60.0, tilt_db_per_octave=6.0, attack_seconds=0, release_seconds=0)
    half_scale = 10 ** (-12 / 20)

    def peak(frequency):
        return analyze(stereo(sine(frequency, 1.0, amplitude=half_scale)), fps=30, settings=tilted)[15].max()

    one_octave_in_db = 6.0 / -tilted.db_floor
    assert peak(2000) - peak(1000) == pytest.approx(one_octave_in_db, abs=0.01)
    assert peak(1000) - peak(500) == pytest.approx(one_octave_in_db, abs=0.01)


DEFAULT_BANDS = np.geomspace(30.0, 16000.0, 513)
DEFAULT_CENTERS = np.sqrt(DEFAULT_BANDS[:-1] * DEFAULT_BANDS[1:])
STILL = dict(attack_seconds=0.0, release_seconds=0.0)
LONG = AnalysisSettings(low_fft_size=16384, **STILL)


def band_of(frequency: float) -> int:
    return int(np.searchsorted(DEFAULT_BANDS, frequency)) - 1


def loud_noise(seconds: float = 3.0) -> np.ndarray:
    return np.random.default_rng(5).standard_normal(round(seconds * SAMPLE_RATE)).astype(np.float32) * 0.5


def test_longer_low_fft_separates_two_bass_notes():
    notes = stereo(sine(55, 3.0, 0.4) + sine(73.4, 3.0, 0.4))
    for settings, merged in ((AnalysisSettings(**STILL), True), (LONG, False)):
        row = analyze(notes, 30, settings)[45]
        dip = row[band_of(55):band_of(73.4) + 1].min() / min(row[band_of(55)], row[band_of(73.4)])
        assert (dip > 0.9) == merged


def test_longer_low_fft_narrows_a_single_bass_note():
    tone = stereo(sine(60, 3.0, 0.5))
    wide = analyze(tone, 30, AnalysisSettings(**STILL))[45]
    narrow = analyze(tone, 30, LONG)[45]
    assert (narrow > narrow.max() / 2).sum() < (wide > wide.max() / 2).sum() / 2


def test_bands_above_the_cross_fade_are_unchanged():
    audio = stereo(loud_noise() + sine(60, 3.0, 0.3))
    plain = analyze(audio, 30, AnalysisSettings())
    blended = analyze(audio, 30, AnalysisSettings(low_fft_size=16384))
    above = DEFAULT_CENTERS >= 250.0 * np.sqrt(2)
    assert np.array_equal(plain[:, above], blended[:, above])
    assert not np.array_equal(plain[:, ~above], blended[:, ~above])


def test_off_by_default_and_crossover_alone_changes_nothing():
    audio = stereo(loud_noise(1.0))
    assert np.array_equal(
        analyze(audio, 30, AnalysisSettings()), analyze(audio, 30, AnalysisSettings(low_crossover_frequency=100.0))
    )


def test_broadband_bass_keeps_about_the_same_level():
    # A longer FFT reads broadband sound about 6 dB lower; without level matching this noise reads 0.016 here.
    below = (DEFAULT_CENTERS > 60) & (DEFAULT_CENTERS < 170)
    plain = analyze(stereo(loud_noise()), 30, AnalysisSettings())[15:75][:, below].mean()
    blended = analyze(stereo(loud_noise()), 30, AnalysisSettings(low_fft_size=16384))[15:75][:, below].mean()
    assert abs(blended - plain) < 0.04


def test_a_kick_still_peaks_on_its_own_frame():
    signal = np.zeros(3 * SAMPLE_RATE, np.float32)
    burst = sine(60, 0.08, 0.8) * np.exp(-np.arange(round(0.08 * SAMPLE_RATE)) / (0.03 * SAMPLE_RATE))
    signal[SAMPLE_RATE:SAMPLE_RATE + len(burst)] = burst
    column = analyze(stereo(signal), 30, LONG)[:, band_of(60)]
    assert abs(int(column.argmax()) - 30) <= 1


@pytest.mark.parametrize("size", [3000, 2048, 4096])
def test_low_fft_size_must_be_a_larger_power_of_two(size):
    with pytest.raises(ValueError, match="low_fft_size"):
        AnalysisSettings(low_fft_size=size)
