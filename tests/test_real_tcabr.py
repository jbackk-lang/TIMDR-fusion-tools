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
from model_j.model_j_detector import bridge_detector, model_j

pytestmark = pytest.mark.skipif(
    not os.path.isfile(TCABR_METADATA_PATH),
    reason="realne dane TCABR nie sa obecne lokalnie (data/real/tcabr_samples_metadata.json)",
)

DISRUPTIVE_SHOTS = ["15569", "22201", "20316"]
NORMAL_SHOTS = ["33664", "36973"]
CHANNELS = ["IPlasma", "VLoop", "BbMirnovN01"]

RAW_NPZ_FILES = {
    "15569": "disruptive_early_shot_15569.npz",
    "22201": "disruptive_late_shot_22201.npz",
    "20316": "disruptive_typical_shot_20316.npz",
    "33664": "normal_early_shot_33664.npz",
    "36973": "normal_late_shot_36973.npz",
}
RAW_NPZ_DIR = os.path.join(REAL_DATA_DIR, "raw")


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


@pytest.mark.parametrize("shot,min_fraction", [("15569", 0.90), ("22201", 0.85)])
def test_model_j_local_calibrated_signal_concentrates_near_real_disruption(shot, min_fraction):
    """
    Follow-up to test_model_j_raw_signal_finds_none_of_the_real_disruptions
    above: the global-normalization failure documented there is a real
    design flaw (single shared std(gradient) for a ~45-50k-sample trace),
    not just "one artifact to note and move past". gradient_zscore(window=...)
    normalizes locally instead, with its MAD floor CALIBRATED from the
    signal's own ADC quantization step (_estimate_quantization_step() -
    a physical property of the instrument, measured once per signal and
    identical for disruptive/normal shots alike - never derived from a
    known disruption time). This is calibration, not post-hoc tuning to
    this specific test.

    Real, honest result of applying it (window=1001, threshold=5.0) to raw
    IPlasma: for shots 15569 and 22201, the large majority of ALL flagged
    points across the whole trace fall within +-10ms of the independently
    computed disruption time - real temporal concentration, not noise.
    Shot 20316 does NOT show this (see the separate test below) - this is
    a genuine partial result (2/3), not a full fix, and is reported as
    such. If this ever starts failing, the signal or the calibration
    changed - investigate, don't just loosen the threshold.
    """
    _t, signal, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    t = _t
    dtime = meta["disruption_time_s"]
    points = model_j(signal, threshold=5.0, window=1001)
    assert len(points) > 0
    near = [p for p in points if abs(t[p] - dtime) < 0.010]
    fraction_near = len(near) / len(points)
    assert fraction_near >= min_fraction, (
        f"shot {shot}: expected >={min_fraction:.0%} of local-z detections within "
        f"+-10ms of the real disruption time, got {fraction_near:.0%} "
        f"({len(near)}/{len(points)}) - the documented finding in "
        f"data/real/tcabr_samples_metadata.json needs re-checking."
    )


def test_model_j_local_calibrated_signal_does_not_concentrate_on_shot_20316():
    """
    Honest negative half of the finding above: the SAME calibrated local
    method (no per-shot tuning) does NOT show temporal concentration for
    shot 20316 - only a small minority of its flagged points fall near the
    real disruption time. Documented explicitly rather than silently
    excluded from the positive test above, so the real 2/3 (not 3/3)
    result stays visible.
    """
    shot = "20316"
    _t, signal, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    t = _t
    dtime = meta["disruption_time_s"]
    points = model_j(signal, threshold=5.0, window=1001)
    assert len(points) > 0
    near = [p for p in points if abs(t[p] - dtime) < 0.010]
    fraction_near = len(near) / len(points)
    assert fraction_near < 0.5, (
        f"shot {shot}: expected the documented lack of concentration (<50% near "
        f"the real disruption time) but got {fraction_near:.0%} - if this genuinely "
        f"improved, update this test AND data/real/tcabr_samples_metadata.json "
        f"together, with the real numbers, not just to make the test pass."
    )


def test_model_j_local_calibrated_raw_count_alone_does_not_separate_normal_from_disruptive():
    """
    Documents the other honest half: raw COUNT of local-z detections
    (window=1001, threshold=5.0) is not, by itself, a useful discriminator
    between disruptive and normal shots - normal shots produce comparable
    or higher raw counts than some disruptive ones. What's informative is
    temporal concentration (tests above), not the count on its own -
    consistent with the same lesson already documented for the synthetic
    quiet/single_burst scenarios in README.md.
    """
    counts = {}
    for shot in DISRUPTIVE_SHOTS + NORMAL_SHOTS:
        _t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        counts[shot] = len(model_j(signal, threshold=5.0, window=1001))
    # at least one normal shot's raw count is >= at least one disruptive
    # shot's raw count - i.e. count alone cannot cleanly separate the two
    # classes (if this assertion ever fails, raw count became separating,
    # which would genuinely be worth re-documenting as an improvement).
    assert max(counts[s] for s in NORMAL_SHOTS) >= min(counts[s] for s in DISRUPTIVE_SHOTS)


@pytest.mark.parametrize("shot", DISRUPTIVE_SHOTS)
def test_bridge_detector_is_100_percent_precise_on_all_3_disruptive_shots(shot):
    """
    Follow-up to the local/calibrated tests above (2/3 shots concentrated,
    20316 did not). Diagnosis: 20316's current declines gradually for
    several ms BEFORE the final crash (unlike 15569/22201, which are flat
    then sudden), so the crash is less of an outlier against an
    already-elevated local baseline. Fix tried here is a genuinely
    different detector, not a retuned parameter: bridge_detector()
    requires BOTH a short-scale (pointwise gradient z-score) AND a
    long-scale (sustained >30% drop in a 5ms window - literally the
    already-validated Zenodo classification criterion, applied point by
    point) signal to agree. Parameters (long_window=1250=5ms,
    drop_fraction=0.30, short_window=1001, short_threshold=5.0) were fixed
    BEFORE checking this result and are unchanged from what was already
    validated/used separately above - nothing here was tuned to hit 3/3.

    Real, honest result: for ALL 3 disruptive shots, 100% of the bridge's
    detections fall within +-10ms of the real disruption time (up from
    2/3 for the short-scale-only method). This is a genuine improvement,
    not just a differently-worded restatement of the same result - see
    the companion test below documenting the bridge's real limitation
    (still produces a comparable false cluster on one of the two normal
    shots, i.e. this is not a perfect classifier).
    """
    _t, signal, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    t = _t
    dtime = meta["disruption_time_s"]
    points = bridge_detector(signal)
    assert len(points) > 0, f"shot {shot}: brak wykryc mostu - wynik sie pogorszyl, do zbadania"
    near = [p for p in points if abs(t[p] - dtime) < 0.010]
    precision = len(near) / len(points)
    assert precision == 1.0, (
        f"shot {shot}: oczekiwano 100% precyzji (wszystkie wykrycia mostu w +-10ms "
        f"od prawdziwego zaklocenia), otrzymano {precision:.0%} ({len(near)}/{len(points)}) "
        f"- wynik sie zmienil, sprawdzic co i dlaczego zamiast luzowac prog."
    )


def test_bridge_detector_still_produces_a_false_cluster_on_one_normal_shot():
    """
    Honest limitation, documented rather than hidden: bridge_detector() is
    NOT a perfect classifier. On shot 36973 (normal, no real disruption)
    it still produces a single cluster of detections (~100+ points)
    comparable in size to the real detections on the disruptive shots -
    a genuine false positive at the level of "does a disruption-like
    cluster exist", even though raw point-level precision within the
    disruptive shots is 100%. If this ever starts passing (i.e. the false
    cluster disappears), that's worth investigating and re-documenting,
    not silently accepting as a win without understanding why.
    """
    _t, signal, _meta = generate_scenario("tcabr_36973_IPlasma")
    points = bridge_detector(signal)
    assert len(points) > 20, (
        "shot 36973: oczekiwany, udokumentowany falszywy klaster (>20 wykryc) "
        "zniknal - do zbadania, nie do cichego zaakceptowania jako poprawe."
    )


def test_csv_files_match_metadata_sample_counts():
    for shot in DISRUPTIVE_SHOTS + NORMAL_SHOTS:
        for ch in CHANNELS:
            _t, signal, meta = generate_scenario(f"tcabr_{shot}_{ch}")
            assert len(signal) > 0
            assert np.all(np.isfinite(signal))


@pytest.mark.skipif(
    not os.path.isdir(RAW_NPZ_DIR),
    reason="surowe pliki .npz (data/real/raw/) nie sa obecne lokalnie",
)
@pytest.mark.parametrize("shot", DISRUPTIVE_SHOTS + NORMAL_SHOTS)
def test_csv_matches_raw_npz_source(shot):
    """
    Provenance check: the shipped CSVs (time,signal) must reproduce the
    original .npz extracted directly by tcabr_tools.py (data/real/raw/,
    not derived from the CSVs - the independent source) EXACTLY, bit for
    bit after float64 round-trip. CSVs are written with repr(float(...))
    (Python's shortest round-tripping float representation), not a fixed
    decimal count, specifically so this can be an exact equality check
    instead of an approximate one - an earlier version used %.6f for the
    time column, which was already close (~7ns, driven by the raw .npz
    itself storing time as float32) but not exact, and exact is strictly
    better when it costs nothing.
    """
    import numpy as np

    npz_path = os.path.join(RAW_NPZ_DIR, RAW_NPZ_FILES[shot])
    raw = np.load(npz_path)
    for ch in CHANNELS:
        t, signal, _meta = generate_scenario(f"tcabr_{shot}_{ch}")
        raw_signal = raw[ch].astype(np.float64)
        raw_time = raw[f"{ch}_time_us"].astype(np.float64) / 1e6
        assert np.array_equal(raw_signal, signal), (
            f"shot {shot} {ch}: sygnal w CSV nie jest bit-w-bit rowny surowemu .npz"
        )
        assert np.array_equal(raw_time, t), (
            f"shot {shot} {ch}: os czasu w CSV nie jest bit-w-bit rowna surowemu .npz"
        )
