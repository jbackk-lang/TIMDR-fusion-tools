"""
Test end-to-end: to samo, co robi demo/run_demo.py, ale jako regresja.
Uzywa PRAWDZIWYCH funkcji bibliotecznych (nie duplikatow z README).
"""
import os

from parsers.csv_parser import load_csv
from timdr.timdr_filter import timdr
from latro.latro_core import latro
from model_j.model_j_detector import model_j

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_CSV = os.path.join(REPO_ROOT, "data", "w7x_mirnov_example.csv")


def test_full_pipeline_runs_and_finds_injected_events():
    time, signal = load_csv(EXAMPLE_CSV)

    reduced = timdr(signal, window=64)
    assert len(reduced) > 0

    lam, tau, rho = latro(signal)
    assert lam > 0
    assert tau > 0
    assert rho > 0

    points = model_j(signal, threshold=2.0)
    # the example signal has 3 injected abrupt events near samples
    # 400, 950, 1600 - model_j should flag something near each region.
    assert len(points) > 0
    for center in (400, 950, 1600):
        assert any(abs(p - center) < 30 for p in points), (
            f"expected a detected point near sample {center}, got {list(points)}"
        )
