import numpy as np

from timdr.timdr_filter import timdr


def test_timdr_exact_multiple_of_window():
    x = np.arange(8)  # window=4 -> two full windows
    out = timdr(x, window=4)
    assert len(out) == 2
    assert out[0] == np.mean([0, 1, 2, 3])
    assert out[1] == np.mean([4, 5, 6, 7])


def test_timdr_keeps_trailing_partial_window_by_default():
    """
    Regression test: timdr() used to silently DROP the last window if it
    wasn't full length, losing the tail of the signal with no warning.
    Default behavior now keeps it as a shorter final window.
    """
    x = np.arange(10)  # window=4 -> windows of size 4, 4, 2
    out = timdr(x, window=4)
    assert len(out) == 3
    assert out[2] == np.mean([8, 9])


def test_timdr_drop_last_true_restores_old_behavior():
    x = np.arange(10)
    out = timdr(x, window=4, drop_last=True)
    assert len(out) == 2


def test_timdr_empty_signal():
    out = timdr(np.array([]), window=4)
    assert len(out) == 0
