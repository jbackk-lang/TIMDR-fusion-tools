import numpy as np
import pytest
import warnings

from model_j.model_j_detector import gradient_zscore, model_j


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
