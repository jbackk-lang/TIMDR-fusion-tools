"""
Walidacja phasespace_funnel_ratio() (model_j/model_j_detector.py) na
wszystkich 54 realnych strzalach TCABR (35 oryginalnych + 19 genuinely
held-out - patrz tests/test_real_tcabr_batch3_geometric.py) - portret
fazowy (IPlasma, VLoop) w oknie zaniku.

STATUS: ta cecha zostala ZNALEZIONA eksploracyjnie (przeszukanie kilku
kandydujacych konstrukcji geometrycznych na oryginalnych 35 strzalach -
patrz ostrzezenie w docstringu phasespace_funnel_ratio()), ale odtad
FAKTYCZNIE zwalidowana na 19 nowych, wczesniej niewidzianych strzalach z
parametrami zamrozonymi PRZED zobaczeniem tych danych - wynik held-out:
12/14 nowych zaklocajacych powyzej progu 1.65, 0/5 falszywych trafien na
nowych normalnych (patrz test_real_tcabr_batch3_geometric.py po pelny
raport). Testy nizej dokumentuja zmierzony wynik na PELNYM, polaczonym
zbiorze 54 strzalow.

Skipped entirely if the real data isn't present locally.
"""
import json
import os

import numpy as np
import pytest

from demo.scenarios import REAL_DATA_DIR, TCABR_METADATA_PATH, generate_scenario
from model_j.model_j_detector import phasespace_funnel_ratio

pytestmark = pytest.mark.skipif(
    not os.path.isfile(TCABR_METADATA_PATH),
    reason="realne dane TCABR nie sa obecne lokalnie (data/real/tcabr_samples_metadata.json)",
)


@pytest.fixture(scope="module")
def funnel_ratio_rows():
    """Liczone RAZ dla calego pliku (nie w kazdym tescie osobno) - czytanie
    35x2 plikow CSV z dysku jest zbyt wolne, zeby powtarzac je 4x."""
    meta = json.load(open(TCABR_METADATA_PATH))
    rows = []
    for s in meta["samples"]:
        shot = s["shot_id"]
        t_i, i_sig, _m = generate_scenario(f"tcabr_{shot}_IPlasma")
        _t_v, v_sig, _m2 = generate_scenario(f"tcabr_{shot}_VLoop")
        ratio = phasespace_funnel_ratio(i_sig, v_sig, exclude_start=2000)
        rows.append((shot, s["disruptive"], ratio))
    return rows


def _permutation_p_value(a, b, n_perm=10000, seed=0):
    """
    Prosty, niezalezny od scipy (repo go nie ma w zaleznosciach) test
    permutacyjny: dwustronny p-value dla obserwowanej roznicy median
    miedzy dwiema niezaleznymi probami. Statystyka i liczba permutacji sa
    ustalone tu wprost, zeby wynik byl odtwarzalny i jawny (nie ukryta
    biblioteka trzecia).
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    observed = abs(np.median(a) - np.median(b))
    combined = np.concatenate([a, b])
    n_a = len(a)
    rng = np.random.RandomState(seed)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(combined)
        diff = abs(np.median(combined[:n_a]) - np.median(combined[n_a:]))
        if diff >= observed:
            count += 1
    return count / n_perm


def test_funnel_ratio_computes_for_almost_all_54_shots(funnel_ratio_rows):
    assert len(funnel_ratio_rows) == 54
    n_valid = sum(1 for (_, _, r) in funnel_ratio_rows if r is not None)
    # zweryfikowane bezposrednio: wszystkie 54 strzaly daja policzalny wynik
    assert n_valid == 54


def test_funnel_ratio_disruptive_shots_tend_to_expand_more_than_normal(funnel_ratio_rows):
    """
    Dokumentuje zmierzony wynik na PELNYM zbiorze 54 strzalow (37
    zaklocajacych + 17 normalnych, po dolaczeniu 19 genuinely held-out -
    patrz test_real_tcabr_batch3_geometric.py). Zaklocajace maja srednio
    wyzszy funnel_ratio (silniejsze "otwieranie sie" trajektorii (I,V) w
    oknie zaniku) niz normalne, z duzym marginesem w medianach.
    """
    disruptive = [r for (_, d, r) in funnel_ratio_rows if d and r is not None]
    normal = [r for (_, d, r) in funnel_ratio_rows if not d and r is not None]
    assert len(disruptive) == 37
    assert len(normal) == 17

    median_dis = float(np.median(disruptive))
    median_norm = float(np.median(normal))
    assert median_dis > median_norm

    p = _permutation_p_value(disruptive, normal, n_perm=10000, seed=0)
    # zmierzone bezposrednio na pelnym zbiorze 54: p < 0.001 (test
    # permutacyjny na roznicy median) - uzywamy luzniejszego progu (0.01)
    # jako regresji, nie dopasowanego dokladnie do jednej cyfry wyniku.
    assert p < 0.01


def test_funnel_ratio_normal_shots_stay_in_a_narrow_band(funnel_ratio_rows):
    """Zmierzone bezposrednio: wszystkie 17 normalnych strzalow (12
    oryginalnych + 5 nowych held-out) maja funnel_ratio w waskim
    przedziale ~1.05-1.64 (promien trajektorii (I,V) prawie sie nie
    zmienia) - zdecydowanie wezszym niz rozrzut zaklocajacych strzalow.
    Granica gorna (2.0) NIE zostala przesunieta przez nowe dane - to samo
    ograniczenie trzyma sie na obu zbiorach."""
    normal = [r for (_, d, r) in funnel_ratio_rows if not d and r is not None]
    assert min(normal) > 1.0
    assert max(normal) < 2.0


def test_funnel_ratio_known_quench_duration_outlier_is_the_most_contracting_shot(funnel_ratio_rows):
    """Ciekawostka udokumentowana w docstringu phasespace_funnel_ratio():
    strzal 21918 (znany wyjatek quench_duration - nietypowo wolny zanik)
    ma tu NAJNIZSZY funnel_ratio ze wszystkich 54 strzalow (trajektoria
    (I,V) SIE SCIAGA, jedyny taki przypadek) - inna, ale tez nietypowa
    cecha niz reszta zaklocajacych strzalow. To NIE naprawia problemu
    21918 (dalej jest odstajacy, tylko w innym kierunku) - test pilnuje,
    zeby ta obserwacja zostala widoczna, gdyby przyszla zmiana kodu jej
    nie unicestwila po cichu."""
    valid = [(shot, r) for (shot, _d, r) in funnel_ratio_rows if r is not None]
    shot_min, ratio_min = min(valid, key=lambda x: x[1])
    assert shot_min == "21918"
    assert ratio_min < 1.0
