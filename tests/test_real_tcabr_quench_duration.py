"""
Validation of quench_duration()/is_fast_quench() (model_j/model_j_detector.py)
on ALL 35 real TCABR shots - a genuinely different kind of feature than
gradient_zscore()/bridge_detector() (those look at local, pointwise/windowed
deviations; this looks at the SHAPE of the decay after the peak). See
data/real/README.md, section "Geometria ksztaltu: czas zaniku" for the full
narrative.

Skipped entirely if the real data isn't present locally.
"""
import os

import numpy as np
import pytest

from demo.scenarios import REAL_DATA_DIR, TCABR_METADATA_PATH, generate_scenario
from model_j.model_j_detector import is_fast_quench, quench_duration

pytestmark = pytest.mark.skipif(
    not os.path.isfile(TCABR_METADATA_PATH),
    reason="realne dane TCABR nie sa obecne lokalnie (data/real/tcabr_samples_metadata.json)",
)

# Strzal 21918 ma udokumentowany, nietypowo wolny zanik (~27.6ms) - jedyny
# znany wyjatek. Trzymany osobno, zeby byl widoczny w testach, nie
# przemilczany przez wykluczenie z petli.
SLOW_DISRUPTIVE_OUTLIER = "21918"


def _all_shot_ids(meta, disruptive):
    return [s["shot_id"] for s in meta["samples"] if s["disruptive"] == disruptive]


def test_fast_disruptive_shots_are_classified_as_fast_quench(_tcabr_meta=None):
    import json

    meta = json.load(open(TCABR_METADATA_PATH))
    disruptive_ids = [s for s in _all_shot_ids(meta, True) if s != SLOW_DISRUPTIVE_OUTLIER]
    assert len(disruptive_ids) == 22

    wrong = []
    for shot in disruptive_ids:
        t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        dt_sample = t[1] - t[0]
        result = is_fast_quench(signal, dt=dt_sample, duration_threshold=0.015, exclude_start=2000)
        if result is not True:
            wrong.append((shot, result))
    assert wrong == [], (
        f"oczekiwano is_fast_quench=True dla wszystkich 22 'szybkich' zaklocajacych "
        f"strzalow (wylaczajac znany wyjatek {SLOW_DISRUPTIVE_OUTLIER}), zawiodly: {wrong}"
    )


def test_slow_disruptive_outlier_is_honestly_misclassified():
    """
    Dokumentuje wprost znane ograniczenie: strzal 21918 ma prawdziwe
    zaklocenie, ale o wyjatkowo wolnym zaniku (~27.6ms, w zakresie
    normalnych strzalow) - is_fast_quench() go BLEDNIE odrzuca. To nie
    zostalo naprawione (brak wystarczajacych danych, by odroznic 'wolne
    prawdziwe zaklocenie' od 'kontrolowany koniec wyladowania' bez ryzyka
    dopasowania do jednego przypadku) - test istnieje, zeby ten blad byl
    widoczny i sledzony, nie ukryty.
    """
    t, signal, _meta = generate_scenario(f"tcabr_{SLOW_DISRUPTIVE_OUTLIER}_IPlasma")
    dt_sample = t[1] - t[0]
    result = is_fast_quench(signal, dt=dt_sample, duration_threshold=0.015, exclude_start=2000)
    assert result is False, (
        f"strzal {SLOW_DISRUPTIVE_OUTLIER}: oczekiwano udokumentowanej bledniej klasyfikacji "
        f"(False), otrzymano {result} - jesli to sie poprawilo, zbadac dlaczego i "
        f"zaktualizowac dokumentacje z prawdziwym wyjasnieniem, nie samo zluzowac test."
    )


def test_all_normal_shots_are_classified_as_not_fast_quench():
    import json

    meta = json.load(open(TCABR_METADATA_PATH))
    normal_ids = _all_shot_ids(meta, False)
    assert len(normal_ids) == 12

    wrong = []
    for shot in normal_ids:
        t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        dt_sample = t[1] - t[0]
        result = is_fast_quench(signal, dt=dt_sample, duration_threshold=0.015, exclude_start=2000)
        if result is not False:
            wrong.append((shot, result))
    assert wrong == [], (
        f"oczekiwano is_fast_quench=False (kontrolowany, lagodny koniec wyladowania) dla "
        f"wszystkich 12 normalnych strzalow, zawiodly: {wrong}"
    )


def test_quench_duration_margin_between_classes_is_large():
    """
    Sprawdza sam margines, nie tylko klasyfikacje przy jednym progu - 22
    'szybkich' zaklocajacych strzalow powinno miescic sie w duzo mniejszym
    zakresie niz wszystkie 12 normalnych, z duza przerwa miedzy nimi
    (>5x, patrz data/real/README.md: ~0.9-3.1ms vs ~19.1-38.4ms)."""
    import json

    meta = json.load(open(TCABR_METADATA_PATH))
    fast_durations = []
    for shot in _all_shot_ids(meta, True):
        if shot == SLOW_DISRUPTIVE_OUTLIER:
            continue
        t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        dt_sample = t[1] - t[0]
        d = quench_duration(signal, dt=dt_sample, exclude_start=2000)
        assert d is not None
        fast_durations.append(d)

    normal_durations = []
    for shot in _all_shot_ids(meta, False):
        t, signal, _meta = generate_scenario(f"tcabr_{shot}_IPlasma")
        dt_sample = t[1] - t[0]
        d = quench_duration(signal, dt=dt_sample, exclude_start=2000)
        assert d is not None
        normal_durations.append(d)

    max_fast = max(fast_durations)
    min_normal = min(normal_durations)
    assert max_fast < min_normal
    assert min_normal / max_fast > 5.0
