import numpy as np
import pandas as pd


def load_csv(path):
    """
    Wczytuje plik CSV z dwiema kolumnami: czas, wartosc (bez zalozen co do
    nazw naglowkow - uzywa pierwszej i drugiej kolumny pozycyjnie, tak jak
    /analyze w api.py). Zwraca (time, signal) jako dwie tablice np.ndarray.

    float_precision="round_trip": domyslny szybki parser liczb
    zmiennoprzecinkowych pandas moze dac wynik rozny o 1 ULP od
    Pythonowego float() dla tego samego tekstu (udokumentowana wlasciwosc
    pandas, nie blad) - wykryte przy weryfikacji, ze CSV-y TCABR w
    data/real/ sa bit-w-bit zgodne z surowymi .npz
    (tests/test_real_tcabr.py::test_csv_matches_raw_npz_source). Tryb
    "round_trip" gwarantuje dokladne odtworzenie zapisanej wartosci.
    """
    df = pd.read_csv(path, float_precision="round_trip")
    if df.shape[1] < 2:
        raise ValueError(f"CSV '{path}' musi miec co najmniej dwie kolumny: czas, wartosc.")
    time = df.iloc[:, 0].to_numpy(dtype=float)
    signal = df.iloc[:, 1].to_numpy(dtype=float)
    return time, signal
