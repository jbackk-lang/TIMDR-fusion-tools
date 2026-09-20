import numpy as np
import pandas as pd


def load_csv(path):
    """
    Wczytuje plik CSV z dwiema kolumnami: czas, wartosc (bez zalozen co do
    nazw naglowkow - uzywa pierwszej i drugiej kolumny pozycyjnie, tak jak
    /analyze w api.py). Zwraca (time, signal) jako dwie tablice np.ndarray.
    """
    df = pd.read_csv(path)
    if df.shape[1] < 2:
        raise ValueError(f"CSV '{path}' musi miec co najmniej dwie kolumny: czas, wartosc.")
    time = df.iloc[:, 0].to_numpy(dtype=float)
    signal = df.iloc[:, 1].to_numpy(dtype=float)
    return time, signal
