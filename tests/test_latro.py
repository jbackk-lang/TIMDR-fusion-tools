import numpy as np
import pytest

from latro.latro_core import latro, latro_windowed
from latro.latro_features import latro_features


def test_latro_basic_values():
    x = [1.0, -2.0, 3.0]
    lam, tau, rho = latro(x)
    assert lam == pytest.approx(5.0)          # max(3) - min(-2)
    assert tau == pytest.approx(2.0)           # mean(|1|,|-2|,|3|) = 2
    assert rho == pytest.approx((1 + 4 + 9) / 3)  # mean(x**2)


def test_latro_empty_raises():
    with pytest.raises(ValueError):
        latro([])


def test_latro_features_matches_latro_core():
    """
    Regression test: latro_features() used to compute tau/rho differently
    from latro_core.latro() (tau=std(signal) instead of mean(|signal|)).
    They must now agree exactly, since latro_features() delegates to latro().
    """
    x = np.random.RandomState(0).normal(size=100)
    lam, tau, rho = latro(x)
    feats = latro_features(x)
    assert feats["lambda"] == pytest.approx(lam)
    assert feats["tau"] == pytest.approx(tau)
    assert feats["rho"] == pytest.approx(rho)


def test_latro_features_keys():
    feats = latro_features([1, 2, 3, 4])
    assert set(feats.keys()) == {"lambda", "tau", "rho"}


def test_latro_windowed_matches_timdr_window_count():
    """
    latro_windowed() must split the signal into exactly the same windows as
    timdr() (same length, same drop_last behavior), so the two can be
    plotted on the same x-axis (reduced_x).
    """
    from timdr.timdr_filter import timdr

    x = np.arange(10, dtype=float)
    reduced = timdr(x, window=4)
    lambdas, taus, rhos = latro_windowed(x, window=4)
    assert len(lambdas) == len(reduced)
    assert len(taus) == len(reduced)
    assert len(rhos) == len(reduced)


def test_latro_windowed_drop_last():
    x = np.arange(10, dtype=float)
    lambdas, taus, rhos = latro_windowed(x, window=4, drop_last=True)
    assert len(lambdas) == 2


def test_latro_windowed_per_window_values():
    # window 1: [0,1,2,3] -> lam=3, tau=mean(|x|)=1.5, rho=mean(x^2)=3.5
    # window 2: [10,10,10,10] -> lam=0, tau=10, rho=100
    x = np.array([0, 1, 2, 3, 10, 10, 10, 10], dtype=float)
    lambdas, taus, rhos = latro_windowed(x, window=4)
    assert lambdas[0] == pytest.approx(3.0)
    assert taus[0] == pytest.approx(1.5)
    assert rhos[0] == pytest.approx(3.5)
    assert lambdas[1] == pytest.approx(0.0)
    assert taus[1] == pytest.approx(10.0)
    assert rhos[1] == pytest.approx(100.0)


def test_latro_windowed_empty_signal():
    lambdas, taus, rhos = latro_windowed(np.array([]), window=4)
    assert len(lambdas) == 0
