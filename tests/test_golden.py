"""Golden hashes of the built-in presets' frames, so any unintended change of a settled look fails the suite.

When a look changes on purpose (or a Skia or NumPy upgrade changes the bytes), check the frames visually first, then
renew the hashes printed by the failing assertion.
"""

import hashlib

import numpy as np
import pytest

from audio_spectrum.analysis import analyze
from audio_spectrum.presets import load_preset
from audio_spectrum.renderer import FrameRenderer
from signals import SAMPLE_RATE, sine, stereo

WIDTH, HEIGHT = 640, 360
FPS = 30
FRAMES = (3, 15, 30, 45, 58)

GOLDEN = {
    "bars": "7755194c13f367a075c17fefd649a4828b0df478163c59e4c0359f40f8403b52",
    "blocks": "69025577c04f1c16e8436a8ef790c0553d7fd4fb6149eeb1da4173abb761bb88",
    "default": "459cd8e8affd68ccdb96816fc700862770773acb2db8973dc3498333f818c191",
    "glow": "ce9dc88596207cad2d4b548e3115245f260ecdeed55f9d098599b1b9f474d499",
    "unity-classic": "922b4c8ab0d942cf6198c046abdf9dd5cecd1f0af8d3afc7f7ec5b7776f7cef4",
}


def generated_audio():
    noise = np.random.default_rng(7).standard_normal(2 * SAMPLE_RATE).astype(np.float32) * 0.05
    left = sine(55, 2.0, 0.3) + sine(880, 2.0, 0.2) + sine(5000, 2.0, 0.1) + noise
    return stereo(left, left * 0.7)


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_builtin_preset_frames_match_their_golden_hash(name):
    preset = load_preset(name)
    values = analyze(generated_audio(), FPS, preset.analysis)
    renderer = FrameRenderer(preset, WIDTH, HEIGHT)
    digest = hashlib.sha256()
    for index in FRAMES:
        digest.update(values[index].tobytes())
        digest.update(renderer.render(values[index]).tobytes())
    assert digest.hexdigest() == GOLDEN[name]
