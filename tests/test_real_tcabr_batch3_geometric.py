"""
Walidacja HELD-OUT (genuinely nowych, wczesniej niewidzianych) 19 strzalow
TCABR dla obu cech geometrycznych (quench_duration()/is_fast_quench() i
phasespace_funnel_ratio()) - z parametrami zamrozonymi PRZED zobaczeniem
tych danych. To jest dokladnie ten sam wzorzec dyscypliny, co walidacja
bridge_detector() na 30 nowych strzalach w test_real_tcabr_batch2.py.

Pochodzenie: uzytkownik wyciagnal 20 KOLEJNYCH, wczesniej niewidzianych
strzalow z Zenodo (5 normalnych + 15 zaklocajacych,
tcabr_new_20_5_normal_15_disruptive/MANIFEST.json,
excluded_previous_shot_ids potwierdza brak powtorzen z oryginalnych 35).
Jeden plik (15_disruptive_shot_17719.npz) byl uszkodzony/obciety w
transferze (BadZipFile - brak poprawnego rekordu konca archiwum ZIP) i
NIE zostal odzyskany - pominiety, stad 19 zamiast 20. Pozostale 19
zostaly przekonwertowane do CSV (bit-exact zweryfikowane przeciw
surowym .npz - patrz test_csv_matches_raw_npz_source w
test_real_tcabr.py, ten sam mechanizm) i dolaczone do glownego
data/real/tcabr_samples_metadata.json (35 -> 54 probek).

Czasy zaklocenia dla nowych 14 zaklocajacych sa wziete WPROST z
MANIFEST.json wygenerowanego przez tcabr_tools.py (niezalezne od tego
repo) - ten sam wzorzec co dla poprzedniej partii 30.

Skipped entirely if the real data isn't present locally.
"""
import json
import os

import numpy as np
import pytest

from demo.scenarios import REAL_DATA_DIR, TCABR_METADATA_PATH, generate_scenario
from model_j.model_j_detector import is_fast_quench, phasespace_funnel_ratio, quench_duration

pytestmark = pytest.mark.skipif(
    not os.path.isfile(TCABR_METADATA_PATH),
    reason="realne dane TCABR nie sa obecne lokalnie (data/real/tcabr_samples_metadata.json)",
)

# Te dokladnie 19 shot_id zostaly dodane w tej partii (held-out) - uzywane
# do odfiltrowania z pelnego zbioru 54, zeby raportowac WYLACZNIE wynik na
# danych, ktorych detektor nie widzial przy kalibracji progow.
NEW_DISRUPTIVE_IDS = [
    "17768", "18566", "20182", "20775", "15502", "16647", "17580", "17763",
    "18042", "17806", "17277", "16422", "20788", "21168",
]
NEW_NORMAL_IDS = ["33666", "34128", "34895", "35758", "36873"]

FUNNEL_RATIO_THRESHOLD = 1.65  # ta sama, wczesniej ustalona granica (patrz phasespace_funnel_ratio() docstring)


@pytest.fixture(scope="module")
def new_batch_rows():
    meta = json.load(open(TCABR_METADATA_PATH))
    wanted = set(NEW_DISRUPTIVE_IDS) | set(NEW_NORMAL_IDS)
    rows = []
    for s in meta["samples"]:
        if s["shot_id"] not in wanted:
            continue
        shot = s["shot_id"]
        t_i, i_sig, _m = generate_scenario(f"tcabr_{shot}_IPlasma")
        _t_v, v_sig, _m2 = generate_scenario(f"tcabr_{shot}_VLoop")
        dt_sample = t_i[1] - t_i[0]
        qd = quench_duration(i_sig, dt=dt_sample, exclude_start=2000)
        fast = is_fast_quench(i_sig, dt=dt_sample, duration_threshold=0.015, exclude_start=2000)
        fr = phasespace_funnel_ratio(i_sig, v_sig, exclude_start=2000)
        rows.append((shot, s["disruptive"], qd, fast, fr))
    return rows


def test_new_batch_csv_matches_raw_npz_source_bit_exact():
    """
    Ten sam bit-exact provenance check co
    tests/test_real_tcabr.py::test_csv_matches_raw_npz_source, ale dla
    tej partii (oryginalne 35 juz maja wlasny test). ZNALEZIONY i
    NAPRAWIONY podczas integracji tej partii: pierwsza wersja skryptu
    konwertujacego uzywala `time_us * 1e-6` zamiast ustalonej konwencji
    `time_us / 1e6` (patrz test_csv_matches_raw_npz_source) - te dwa
    dawaly rozne wyniki na ostatnim bicie mantysy dla ~29% probek (nie
    kosmetyczne zaokraglenie, realna niezgodnosc z reszta repo).
    Przeliczono wszystkie 57 plikow CSV tej partii (19 strzalow x 3
    kanaly) przez `/1e6`, ten test pilnuje regresji.
    """
    meta = json.load(open(TCABR_METADATA_PATH))
    wanted = set(NEW_DISRUPTIVE_IDS) | set(NEW_NORMAL_IDS)
    raw_files = os.listdir(os.path.join(REAL_DATA_DIR, "raw"))

    checked = 0
    for s in meta["samples"]:
        if s["shot_id"] not in wanted:
            continue
        raw_name = next(f for f in raw_files if f.endswith(f"shot_{s['shot_id']}.npz"))
        raw = np.load(os.path.join(REAL_DATA_DIR, "raw", raw_name))
        for ch in s["channels"]:
            channel = ch["channel"]
            t, signal, _meta = generate_scenario(f"tcabr_{s['shot_id']}_{channel}")
            raw_signal = raw[channel].astype(np.float64)
            raw_time = raw[f"{channel}_time_us"].astype(np.float64) / 1e6
            assert np.array_equal(raw_signal, signal), (
                f"shot {s['shot_id']} {channel}: sygnal w CSV nie jest bit-w-bit rowny surowemu .npz"
            )
            assert np.array_equal(raw_time, t), (
                f"shot {s['shot_id']} {channel}: os czasu w CSV nie jest bit-w-bit rowna surowemu .npz"
            )
            checked += 1
    assert checked == 57  # 19 strzalow x 3 kanaly


def test_new_batch_has_exactly_19_shots(new_batch_rows):
    assert len(new_batch_rows) == 19
    assert sum(1 for (_, d, *_r) in new_batch_rows if d) == 14
    assert sum(1 for (_, d, *_r) in new_batch_rows if not d) == 5


def test_is_fast_quench_perfect_on_held_out_batch(new_batch_rows):
    """Zmierzone bezposrednio: is_fast_quench() (prog 15ms, zamrozony
    przed zobaczeniem tych 19 strzalow) klasyfikuje WSZYSTKIE 14 nowych
    zaklocajacych jako True i WSZYSTKIE 5 nowych normalnych jako False -
    0 bledow na tym konkretnym held-out zbiorze (w odroznieniu od
    oryginalnych 35, gdzie jest jeden znany wyjatek, 21918 - w tej
    partii takiego przypadku nie bylo)."""
    wrong = [(shot, dis, fast) for (shot, dis, _qd, fast, _fr) in new_batch_rows if fast != dis]
    assert wrong == [], f"is_fast_quench pomylil sie na held-out danych: {wrong}"


def test_funnel_ratio_on_held_out_batch_matches_measured_result(new_batch_rows):
    """
    Zmierzone bezposrednio na tych 19 strzalach (parametry
    phasespace_funnel_ratio() NIEZMIENIONE wzgledem tego, co bylo
    zamrozone przy odkryciu na oryginalnych 35): 12/14 nowych
    zaklocajacych powyzej progu 1.65, 0/5 falszywych trafien na nowych
    normalnych. To NIE jest idealny klasyfikator (2 nowe zaklocajace
    strzaly, 18566 i 20182, wypadaja ponizej progu - podobnie jak znany
    wyjatek 21918 w oryginalnym zbiorze), ale 100% swoistosc + 86%
    czulosc na genuinely held-out danych to realne potwierdzenie, ze to
    nie byl przypadek dopasowany do oryginalnych 35.
    """
    dis_ratios = [(shot, fr) for (shot, dis, _qd, _fast, fr) in new_batch_rows if dis]
    norm_ratios = [(shot, fr) for (shot, dis, _qd, _fast, fr) in new_batch_rows if not dis]
    assert len(dis_ratios) == 14
    assert len(norm_ratios) == 5

    dis_above = [shot for (shot, fr) in dis_ratios if fr is not None and fr > FUNNEL_RATIO_THRESHOLD]
    norm_above = [shot for (shot, fr) in norm_ratios if fr is not None and fr > FUNNEL_RATIO_THRESHOLD]

    assert len(dis_above) == 12, f"oczekiwano 12/14, otrzymano {len(dis_above)}: {dis_above}"
    assert norm_above == [], f"oczekiwano 0 falszywych trafien na normalnych, otrzymano: {norm_above}"


def test_funnel_ratio_new_normal_shots_stay_below_old_normal_maximum(new_batch_rows):
    """Dodatkowa kontrola specyficzna dla held-out: 5 nowych normalnych
    strzalow powinno trzymac sie POD tym samym gornym ograniczeniem
    (~1.64), co 12 oryginalnych normalnych - czyli nowe dane NIE
    przesuwaja granicy normalnego zachowania w gore."""
    norm_ratios = [fr for (_shot, dis, _qd, _fast, fr) in new_batch_rows if not dis and fr is not None]
    assert len(norm_ratios) == 5
    assert max(norm_ratios) < 1.64
