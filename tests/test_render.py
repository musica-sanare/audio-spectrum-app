import numpy as np
import pytest

from audio_spectrum.geometry import flat_quads, perspective_quads
from audio_spectrum.presets import GREEN_BACK, WHITE, FlatLook, PerspectiveLook, Preset, builtin_preset_names, load_preset
from audio_spectrum.renderer import FrameRenderer

WIDTH, HEIGHT = 640, 360


def test_flat_quads_stay_inside_the_margins():
    look = FlatLook(margin_x=0.1)
    quads = flat_quads(look, np.ones(64), WIDTH, HEIGHT)
    assert quads.shape == (64, 4, 2)
    assert quads[:, :, 0].min() >= 0.1 * WIDTH - look.min_bar_width_px
    assert quads[:, :, 0].max() <= 0.9 * WIDTH + look.min_bar_width_px


def test_flat_quads_mirror_around_the_baseline_and_scale_with_value():
    look = FlatLook(baseline_y=0.5, max_height=0.3, response=1.0)
    quads = flat_quads(look, np.array([0.0, 0.5, 1.0]), WIDTH, HEIGHT)
    tops = quads[:, 0, 1]
    bottoms = quads[:, 2, 1]
    baseline = HEIGHT / 2
    np.testing.assert_allclose(baseline - tops, bottoms - baseline)
    np.testing.assert_allclose(baseline - tops, [look.min_height_px, 0.15 * HEIGHT, 0.3 * HEIGHT])


def test_flat_quads_without_mirror_grow_upward_only():
    quads = flat_quads(FlatLook(mirror=False), np.ones(4), WIDTH, HEIGHT)
    assert np.all(quads[:, 2, 1] == HEIGHT / 2)


def test_flat_bars_are_never_thinner_than_the_minimum_width():
    look = FlatLook(min_bar_width_px=2.0)
    quads = flat_quads(look, np.ones(1000), WIDTH, HEIGHT)
    assert np.all(quads[:, 1, 0] - quads[:, 0, 0] >= 2.0 - 1e-9)


def blocks(**settings) -> FlatLook:
    return FlatLook(style="blocks", response=1.0, block_height_px=8.0, block_gap_px=3.0, **settings)


def segment_spans(quads: np.ndarray) -> list[tuple[float, float]]:
    return sorted((float(quad[:, 1].min()), float(quad[:, 1].max())) for quad in quads)


def test_blocks_draw_only_the_segments_a_bar_fully_reaches():
    # Full scale is 36 px on each side; segments start 1.5 px from the baseline and repeat every 11 px.
    look = blocks(max_height=0.1, mirror=False)
    quads = flat_quads(look, np.array([0.0, 0.25, 0.5, 1.0]), WIDTH, HEIGHT)
    counts = np.bincount(np.round(quads[:, 0, 0]).astype(int))
    assert sorted(counts[counts > 0]) == [1, 1, 3]
    assert segment_spans(flat_quads(look, np.array([1.0]), WIDTH, HEIGHT)) == [
        (150.0, 158.0), (161.0, 169.0), (172.0, 180.0)
    ]


def test_mirrored_blocks_keep_a_gap_around_the_baseline():
    quads = flat_quads(blocks(max_height=0.1), np.array([1.0]), WIDTH, HEIGHT)
    assert segment_spans(quads) == [
        (148.5, 156.5), (159.5, 167.5), (170.5, 178.5), (181.5, 189.5), (192.5, 200.5), (203.5, 211.5)
    ]


def test_blocks_keep_the_bar_positions_and_widths():
    values = np.full(16, 1.0)
    bars = flat_quads(FlatLook(response=1.0), values, WIDTH, HEIGHT)
    segments = flat_quads(blocks(), values, WIDTH, HEIGHT)
    assert set(np.round(segments[:, 0, 0], 6)) == set(np.round(bars[:, 0, 0], 6))
    assert set(np.round(segments[:, 1, 0], 6)) == set(np.round(bars[:, 1, 0], 6))


def test_silent_blocks_draw_nothing_and_render_the_background():
    look = blocks()
    assert flat_quads(look, np.zeros(8), WIDTH, HEIGHT).shape == (0, 4, 2)
    frame = FrameRenderer(Preset(name="test", look=look), WIDTH, HEIGHT).render(np.zeros(8))
    assert np.all(frame == (0, 0, 255))


def test_blocks_never_grow_past_the_full_scale_height():
    quads = flat_quads(blocks(max_height=0.1), np.array([5.0]), WIDTH, HEIGHT)
    assert quads[:, :, 1].min() >= HEIGHT / 2 - 0.1 * HEIGHT


def test_perspective_box_on_the_camera_axis_projects_to_the_horizontal_center():
    look = PerspectiveLook(first_x=0.0)
    quads = perspective_quads(look, np.array([0.05]), WIDTH, HEIGHT)
    assert quads[0, :, 0].mean() == pytest.approx(WIDTH / 2)


def test_perspective_baseline_sits_above_the_center_because_the_camera_looks_down():
    quads = perspective_quads(PerspectiveLook(first_x=0.0), np.array([0.0]), WIDTH, HEIGHT)
    assert quads[0, :, 1].mean() < HEIGHT / 2


def test_render_draws_foreground_on_the_chosen_background():
    preset = Preset(name="test", look=FlatLook(margin_x=0.0, bar_fill=1.0), background=GREEN_BACK)
    frame = FrameRenderer(preset, WIDTH, HEIGHT).render(np.ones(32))
    assert frame.shape == (HEIGHT, WIDTH, 3)
    assert frame.dtype == np.uint8
    assert tuple(frame[0, 0]) == GREEN_BACK
    assert tuple(frame[HEIGHT // 2, WIDTH // 2]) == WHITE


@pytest.mark.parametrize("name", builtin_preset_names())
def test_builtin_presets_render_deterministically(name):
    preset = load_preset(name)
    values = np.random.default_rng(0).random(preset.analysis.bands).astype(np.float32) * 0.2
    renderer = FrameRenderer(preset, WIDTH, HEIGHT)
    first = renderer.render(values)
    assert np.array_equal(first, renderer.render(values))
    assert np.any(np.all(first == preset.foreground, axis=2))
