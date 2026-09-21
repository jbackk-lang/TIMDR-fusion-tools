import numpy as np
import pytest
import warnings

from model_j.model_j_detector import (
    bridge_detector,
    gradient_zscore,
    is_fast_quench,
    model_j,
    quench_duration,
    sustained_drop_mask,
)


def test_model_j_empty_signal_returns_empty():
    result = model_j(np.array([]))
    assert len(result) == 0


def test_model_j_constant_signal_no_divide_by_zero():
    """
    Regression test for the confirmed bug: model_j() on a constant signal
    used to compute 0/0 (std(gradient) == 0), raising
    'RuntimeWarning: invalid value encountered in divide' and returning
    an empty result without any indication something went wrong.

    It must now return an empty result WITHOUT raising or warning.
    """
    x = np.ones(50)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # promote any warning to an error
        result = model_j(x)
    assert len(result) == 0


def test_model_j_linear_ramp_no_divide_by_zero():
    """A perfectly linear ramp also has a constant gradient (std == 0)."""
    x = np.linspace(0, 10, 100)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = model_j(x)
    assert len(result) == 0


def test_model_j_detects_injected_spike():
    x = np.zeros(100)
    x[50] = 10.0  # sharp isolated spike -> large local gradient z-score
    result = model_j(x, threshold=2.0)
    assert len(result) > 0
    assert any(45 <= i <= 55 for i in result)


def test_gradient_zscore_empty_signal_returns_empty():
    assert len(gradient_zscore(np.array([]))) == 0


def test_gradient_zscore_constant_signal_returns_empty_no_warning():
    x = np.ones(50)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        z = gradient_zscore(x)
    assert len(z) == 0


def test_gradient_zscore_has_zero_mean_and_unit_std_when_nonflat():
    rng = np.random.RandomState(0)
    x = rng.normal(size=200)
    z = gradient_zscore(x)
    assert len(z) == len(x)
    assert z.mean() == pytest.approx(0.0, abs=1e-9)
    assert z.std() == pytest.approx(1.0, abs=1e-9)


def test_gradient_zscore_local_mode_matches_global_shape_and_length():
    """window=... (local mode) must return the same length as global mode
    and stay finite - basic sanity check independent of the real-data
    behavior covered in tests/test_real_tcabr.py."""
    rng = np.random.RandomState(2)
    x = rng.normal(size=2000)
    z_local = gradient_zscore(x, window=201)
    assert len(z_local) == len(x)
    assert np.all(np.isfinite(z_local))


def test_gradient_zscore_local_mode_resists_a_single_large_artifact():
    """Regression for the real problem this mode was built for: one huge
    isolated spike must not suppress sensitivity to a real, separate event
    elsewhere in the same signal - unlike global mode, where a single
    outlier inflates the one shared std(gradient) for the whole signal."""
    rng = np.random.RandomState(3)
    x = rng.normal(scale=0.1, size=3000)
    x[0] += 500.0  # huge, isolated, start-of-signal artifact (like the real TCABR case)
    x[1500:1510] += 5.0  # separate, smaller, real-looking event far from the artifact

    z_global = gradient_zscore(x)
    z_local = gradient_zscore(x, window=201)

    # global mode: the artifact should dominate, leaving little/no margin
    # to flag the smaller separate event
    global_hits_near_event = np.sum(np.abs(z_global[1490:1520]) > 2.0)
    # local mode: normalizing against nearby background instead of the
    # whole signal should still catch the separate event
    local_hits_near_event = np.sum(np.abs(z_local[1490:1520]) > 2.0)

    assert local_hits_near_event > global_hits_near_event


def test_gradient_zscore_local_mode_survives_quantized_flat_regions():
    """Regression for the real numerical failure found on raw TCABR data:
    naive local MAD collapses to ~0 in flat, coarsely-quantized regions,
    blowing up z-scores to meaningless values (millions+). The
    quantization-calibrated floor (_estimate_quantization_step(), a
    measured physical property of the signal, not a tuned constant) must
    keep results bounded even on a heavily quantized synthetic signal."""
    rng = np.random.RandomState(4)
    # simulate coarse ADC quantization: round a smooth signal to a visible step
    t = np.linspace(0, 1, 4000)
    raw = 10 * np.sin(2 * np.pi * 3 * t) + rng.normal(scale=0.05, size=4000)
    step = 0.5
    quantized = np.round(raw / step) * step

    z_local = gradient_zscore(quantized, window=201)
    assert np.all(np.isfinite(z_local))
    assert np.max(np.abs(z_local)) < 1000  # bounded, not millions/billions


def test_estimate_quantization_step_measures_the_actual_step():
    from model_j.model_j_detector import _estimate_quantization_step

    x = np.round(np.linspace(0, 10, 500) / 0.25) * 0.25
    step = _estimate_quantization_step(x)
    assert step == pytest.approx(0.25, abs=1e-9)


def test_sustained_drop_mask_empty_signal_returns_empty():
    assert len(sustained_drop_mask(np.array([]))) == 0


def test_sustained_drop_mask_flags_a_genuine_sustained_drop():
    x = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 10.0, 50), np.full(2000, 10.0)])
    mask = sustained_drop_mask(x, window=200, drop_fraction=0.30)
    assert np.any(mask[2000:2100])


def test_sustained_drop_mask_does_not_flag_a_flat_signal():
    x = np.full(3000, 42.0)
    mask = sustained_drop_mask(x, window=200, drop_fraction=0.30)
    assert not np.any(mask)


def test_bridge_detector_empty_signal_returns_empty():
    assert len(bridge_detector(np.array([]))) == 0


def test_bridge_detector_requires_both_scales_to_agree():
    """A sustained RISE (passes the short/pointwise scale - large gradient
    z-score - but can never satisfy sustained_drop_mask(), which only
    fires on decreases from a recent peak) must not be flagged by the
    bridge - that's the whole point of requiring both scales to agree, not
    just one."""
    rng = np.random.RandomState(5)
    x = np.concatenate(
        [
            np.zeros(2000) + rng.normal(scale=0.01, size=2000),
            np.linspace(0.0, 50.0, 60) + rng.normal(scale=0.01, size=60),
            np.full(2000, 50.0) + rng.normal(scale=0.01, size=2000),
        ]
    )
    result = bridge_detector(x, long_window=200, short_window=101, exclude_start=0)
    # no detections near the rise itself (a stray chance false positive from
    # background gaussian noise elsewhere in the signal is not the point
    # being tested here)
    assert not np.any((result > 1900) & (result < 2200))


def test_bridge_detector_flags_a_genuine_sustained_drop():
    rng = np.random.RandomState(6)
    x = np.concatenate(
        [
            100.0 + rng.normal(scale=0.05, size=3000),
            np.linspace(100.0, 5.0, 60) + rng.normal(scale=0.05, size=60),
            5.0 + rng.normal(scale=0.05, size=3000),
        ]
    )
    result = bridge_detector(x, long_window=300, short_window=201, exclude_start=0)
    assert len(result) > 0
    assert np.any((result > 2900) & (result < 3200))


def test_quench_duration_empty_signal_returns_none():
    assert quench_duration(np.array([])) is None


def test_quench_duration_no_decay_returns_none():
    """A signal that never drops below fraction_low after its peak has no
    measurable quench duration."""
    x = np.linspace(0, 100, 2000)  # monotonically rising, never decays
    assert quench_duration(x) is None


def test_quench_duration_measures_a_fast_decay():
    x = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 0.0, 5), np.full(2000, 0.0)])
    dur = quench_duration(x, dt=1.0, smooth_window=1)
    assert dur is not None
    assert 0 < dur < 20  # sharp, few-sample collapse


def test_quench_duration_measures_a_slow_decay():
    x = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 0.0, 500), np.full(2000, 0.0)])
    dur = quench_duration(x, dt=1.0, smooth_window=1)
    assert dur is not None
    assert dur > 100  # gradual, many-sample decline


def test_quench_duration_distinguishes_fast_from_slow_decay():
    fast = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 0.0, 5), np.full(2000, 0.0)])
    slow = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 0.0, 500), np.full(2000, 0.0)])
    dur_fast = quench_duration(fast, dt=1.0, smooth_window=1)
    dur_slow = quench_duration(slow, dt=1.0, smooth_window=1)
    assert dur_fast < dur_slow


def test_is_fast_quench_true_for_sharp_collapse():
    x = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 0.0, 5), np.full(2000, 0.0)])
    assert is_fast_quench(x, dt=1.0, duration_threshold=50, smooth_window=1) is True


def test_is_fast_quench_false_for_gradual_decline():
    x = np.concatenate([np.full(2000, 100.0), np.linspace(100.0, 0.0, 500), np.full(2000, 0.0)])
    assert is_fast_quench(x, dt=1.0, duration_threshold=50, smooth_window=1) is False


def test_is_fast_quench_returns_none_when_no_decay():
    x = np.full(500, 42.0)
    assert is_fast_quench(x) is None


def test_model_j_is_exactly_the_thresholded_gradient_zscore():
    """model_j() must be a thin wrapper over gradient_zscore() - same
    single definition of the z-score used everywhere in this repo
    (dashboard histogram in api.py included), not a second copy."""
    rng = np.random.RandomState(1)
    x = rng.normal(size=300)
    x[150] += 20.0  # inject an obvious spike
    threshold = 1.5
    z = gradient_zscore(x)
    expected = np.where(np.abs(z) > threshold)[0]
    actual = model_j(x, threshold=threshold)
    assert np.array_equal(actual, expected)
