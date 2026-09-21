"""
Independent generalization validation of bridge_detector() (see
model_j/model_j_detector.py and data/real/README.md, section "Walidacja
na 30 nowych strzalach") on 30 real TCABR shots (20 disruptive + 10
normal) extracted by the user AFTER bridge_detector()'s parameters were
already fixed and committed - none of these 30 shots were used to build
or tune the detector. This is a true held-out test, not a second round of
fitting.

Skipped entirely if the real data isn't present locally.
"""
import os

import numpy as np
import pytest

from demo.scenarios import REAL_DATA_DIR, TCABR_METADATA_PATH, generate_scenario
from model_j.model_j_detector import bridge_detector

pytestmark = pytest.mark.skipif(
    not os.path.isfile(TCABR_METADATA_PATH),
    reason="realne dane TCABR nie sa obecne lokalnie (data/real/tcabr_samples_metadata.json)",
)

CHANNELS = ["IPlasma", "VLoop", "BbMirnovN01"]
RAW_NPZ_DIR = os.path.join(REAL_DATA_DIR, "raw")

# 20 nowych zaklocajacych strzalow - dt_s wziete wprost z MANIFEST.json
# tcabr_tools.py (niezalezne od tego repo), expected_precision to
# rzeczywisty, zmierzony wynik bridge_detector() (parametry niezmienione)
# na kazdym z nich - udokumentowany fakt, nie oczekiwanie do dostrojenia.
NEW_DISRUPTIVE = {
    "22243": {"dt": 0.0500, "expected_precision": 1.00},
    "17748": {"dt": 0.0521, "expected_precision": 1.00},
    "20027": {"dt": 0.0641, "expected_precision": 1.00},
    "18560": {"dt": 0.0641, "expected_precision": 1.00},
    "18597": {"dt": 0.0690, "expected_precision": None},  # zero wykryc, patrz test osobny
    "18593": {"dt": 0.0690, "expected_precision": None},  # zero wykryc, patrz test osobny
    "21918": {"dt": 0.0721, "expected_precision": 1.00},
    "18727": {"dt": 0.0722, "expected_precision": 1.00},
    "20950": {"dt": 0.0742, "expected_precision": 0.75},
    "17775": {"dt": 0.0742, "expected_precision": 1.00},
    "17077": {"dt": 0.0773, "expected_precision": 1.00},
    "16999": {"dt": 0.0774, "expected_precision": 1.00},
    "16667": {"dt": 0.0809, "expected_precision": 1.00},
    "16653": {"dt": 0.0810, "expected_precision": 1.00},
    "16646": {"dt": 0.0836, "expected_precision": 58 / 87},
    "16642": {"dt": 0.0836, "expected_precision": 1.00},
    "17439": {"dt": 0.0872, "expected_precision": 1.00},
    "16456": {"dt": 0.0872, "expected_precision": 1.00},
    "19896": {"dt": 0.1112, "expected_precision": 1.00},
    "17578": {"dt": 0.1115, "expected_precision": 1.00},
}
ZERO_DETECTION_SHOTS = ["18597", "18593"]
NONZERO_DISRUPTIVE = {k: v for k, v in NEW_DISRUPTIVE.items() if k not in ZERO_DETECTION_SHOTS}

NEW_NORMAL = [
    "33665", "33874", "34077", "34518", "34776",
    "35008", "35363", "35817", "36096", "36874",
]


@pytest.mark.parametrize("shot", list(NONZERO_DISRUPTIVE.keys()))
def test_bridge_detector_precision_on_new_unseen_disruptive_shots(shot):
    """
    Real, honest, measured precision of bridge_detector() (unchanged
    parameters - long_window=1250, drop_fraction=0.30, short_window=1001,
    short_threshold=5.0) on a shot NEVER seen while building the detector.
    Precision here means: of all points bridge_detector() flags, what
    fraction fall within +-10ms of the real, independently-labeled
    disruption time (see data/real/README.md for full context - this
    number is NOT the same as classifier specificity, see the normal-shot
    tests below).
    """
    expected = NONZERO_DISRUPTIVE[shot]["expected_precision"]
    dt = NONZERO_DISRUPTIVE[shot]["dt"]
    t, signal, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    assert meta["disruption_time_s"] == pytest.approx(dt, abs=0.001)
    points = bridge_detector(signal)
    assert len(points) > 0, f"shot {shot}: oczekiwano wykryc, dostano 0 - wynik sie pogorszyl"
    near = sum(1 for p in points if abs(t[p] - dt) < 0.010)
    precision = near / len(points)
    assert precision == pytest.approx(expected, abs=1e-6), (
        f"shot {shot}: oczekiwano precyzji {expected:.0%}, otrzymano {precision:.0%} "
        f"({near}/{len(points)}) - wynik sie zmienil, zbadac zamiast luzowac oczekiwanie."
    )


@pytest.mark.parametrize("shot", ZERO_DETECTION_SHOTS)
def test_bridge_detector_still_misses_the_two_known_fast_collapse_shots(shot):
    """
    Honest negative half of the validation, kept visible rather than
    filtered out of the parametrize list above. Shots 18597 and 18593
    both collapse unusually fast (near-zero current within ~4-5ms of dt,
    with NO preceding flat period - unlike most other shots), a plausible
    continuation of the same self-contamination mechanism diagnosed for
    shot 20316 in the local-mode tests: the crash fills too much of the
    1001-sample short-scale window to stand out against it. Not patched
    here - documented as a known, understood failure mode.
    """
    dt = NEW_DISRUPTIVE[shot]["dt"]
    t, signal, meta = generate_scenario(f"tcabr_{shot}_IPlasma")
    assert meta["disruption_time_s"] == pytest.approx(dt, abs=0.001)
    points = bridge_detector(signal)
    assert len(points) == 0, (
        f"shot {shot}: oczekiwano udokumentowanego braku wykryc, dostano {len(points)} "
        f"- to poprawa, do zbadania i przepisania tego testu z wyjasnieniem, nie do "
        f"cichego zaakceptowania."
    )


def test_bridge_detector_generalization_summary_matches_documented_rates():
    """
    Aggregate check on the headline numbers quoted in data/real/README.md
    ("Walidacja na 30 nowych strzalach"): 16/20 shots at 100% precision,
    2/20 with zero detections, average precision ~96.8% where detections
    exist. A single aggregate assertion so the documented summary can't
    silently drift from the per-shot tests above.
    """
    precisions = []
    zero_count = 0
    hundred_count = 0
    for shot, info in NEW_DISRUPTIVE.items():
        dt = info["dt"]
        _t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        t = _t
        points = bridge_detector(signal)
        if len(points) == 0:
            zero_count += 1
            continue
        near = sum(1 for p in points if abs(t[p] - dt) < 0.010)
        precision = near / len(points)
        precisions.append(precision)
        if precision == 1.0:
            hundred_count += 1

    assert zero_count == 2
    assert hundred_count == 16
    assert np.mean(precisions) == pytest.approx(0.968, abs=0.005)


def test_bridge_detector_normal_shots_still_produce_false_detections():
    """
    Confirms the honest limitation documented in data/real/README.md:
    bridge_detector() is a within-event LOCALIZER (validated above), not a
    disruptive-vs-normal CLASSIFIER. All 10 new normal shots still produce
    nonzero detections, and several produce a single dominant cluster
    comparable in size to real disruptions - so detection count/cluster
    size alone cannot be used to decide "is this shot disruptive" without
    already knowing a candidate event exists.
    """
    counts = {}
    for shot in NEW_NORMAL:
        _t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        counts[shot] = len(bridge_detector(signal))
    assert all(n > 0 for n in counts.values()), (
        f"oczekiwano falszywych wykryc na wszystkich normalnych strzalach, "
        f"dostano zero dla: {[s for s, n in counts.items() if n == 0]} - "
        f"to poprawa swoistosci, warta zbadania i udokumentowania, nie cichego "
        f"zaakceptowania."
    )
