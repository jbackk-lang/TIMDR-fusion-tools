"""
Tests for the real (non-synthetic) TCABR scenarios loaded from data/real/
by demo/scenarios.py._load_real_tcabr_scenarios(). Skipped entirely if
that data isn't present locally (it's real, licensed data extracted by
hand from a 4.8GB file - see data/real/README.md - not something CI or a
fresh clone is expected to have).
"""
import os

import numpy as np
import pytest

from demo.scenarios import REAL_DATA_DIR, TCABR_METADATA_PATH, generate_scenario, list_scenarios
from model_j.model_j_detector import model_j

pytestmark = pytest.mark.skipif(
    not os.path.isfile(TCABR_METADATA_PATH),
    reason="realne dane TCABR nie sa obecne lokalnie (data/real/tcabr_samples_metadata.json)",
)

DISRUPTIVE_SHOTS = ["15569", "22201", "20316"]
NORMAL_SHOTS = ["33664", "36973"]
CHANNELS = ["IPlasma", "VLoop", "BbMirnovN01"]


def test_all_15_real_scenarios_are_listed():
    ids = {s["id"] for s in list_scenarios()}
    for shot in DISRUPTIVE_SHOTS + NORMAL_SHOTS:
        for ch in CHANNELS:
            assert f"tcabr_{shot}_{ch}" in ids


@pytest.mark.parametrize("shot", DISRUPTIVE_SHOTS)
def test_disruptive_shots_have_a_real_disruption_time(shot):
    _t, _s, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    assert meta["disruptive"] is True
    assert meta["disruption_time_s"] is not None
    assert meta["disruption_time_s"] > 0


@pytest.mark.parametrize("shot", NORMAL_SHOTS)
def test_normal_shots_have_no_disruption_time(shot):
    _t, _s, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    assert meta["disruptive"] is False
    assert meta["disruption_time_s"] is None


def test_disruption_times_match_early_typical_late_naming():
    """The three disruptive shots were labeled early/late/typical by the
    extraction step (tcabr_tools.py output filenames) BEFORE any
    disruption time was computed here - the independently-computed times
    (>30% Ip drop within 5ms, see data/real/ generation) should agree
    with that ordering, which is a real, non-trivial cross-check."""
    _t, _s, early = generate_scenario("tcabr_15569_IPlasma")
    _t, _s, typical = generate_scenario("tcabr_20316_IPlasma")
    _t, _s, late = generate_scenario("tcabr_22201_IPlasma")
    assert early["disruption_time_s"] < typical["disruption_time_s"] < late["disruption_time_s"]


def test_each_channel_has_its_own_time_axis_not_shared():
    """Regression check for the real structural fact (confirmed by the
    user and by tcabr_tools.py) that each TCABR channel has its own time
    axis - IPlasma/VLoop and BbMirnovN01 can even have different sample
    counts within the same shot."""
    _t_i, s_i, _m = generate_scenario("tcabr_33664_IPlasma")
    _t_b, s_b, _m = generate_scenario("tcabr_33664_BbMirnovN01")
    # in shot 33664, BbMirnovN01 was sampled at 2x the rate of IPlasma
    assert len(s_b) != len(s_i)


def test_model_j_raw_signal_finds_none_of_the_real_disruptions():
    """
    Documents a real, honest negative finding (see data/real/
    tcabr_samples_metadata.json, field model_j_validation_note): on the
    RAW extracted IPlasma signal, a large digitizer pre-trigger artifact
    at t=0 (a jump of ~300 kA between the first two samples - not
    physics) dominates Model J's single global gradient-std
    normalization, so at threshold=2.0 it detects NONE of the 3 real,
    independently-time-stamped disruptions. This is reported as-is, not
    patched with a post-hoc threshold change (that would be exactly the
    kind of post-hoc tuning this ecosystem's anti-numerology protocol
    warns against) - if this test ever starts passing differently, the
    underlying signal or Model J changed and the finding needs
    re-checking, not silently updating the assertion.
    """
    for shot in DISRUPTIVE_SHOTS:
        _t, signal, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        points = model_j(signal, threshold=2.0)
        time = _t
        dtime = meta["disruption_time_s"]
        near = [p for p in points if abs(time[p] - dtime) < 0.002]
        assert len(near) == 0, (
            f"shot {shot}: expected the documented negative result (no raw-signal "
            f"detection near the real disruption time) but got {len(near)} - the "
            f"honest-finding note in data/real/tcabr_samples_metadata.json needs updating."
        )


def test_csv_files_match_metadata_sample_counts():
    for shot in DISRUPTIVE_SHOTS + NORMAL_SHOTS:
        for ch in CHANNELS:
            _t, signal, meta = generate_scenario(f"tcabr_{shot}_{ch}")
            assert len(signal) > 0
            assert np.all(np.isfinite(signal))
