import numpy as np
import warnings

from model_j.model_j_detector import model_j


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
