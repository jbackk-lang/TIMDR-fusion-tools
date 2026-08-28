import numpy as np
import pandas as pd


def load_csv(path):
    """
    Wczytuje sygnal z pliku CSV o dwoch kolumnach: czas, wartosc
    (z naglowkiem w pierwszym wierszu).

    Zwraca:
      (time, signal) jako dwie tablice np.ndarray.
    """
    df = pd.read_csv(path)
    time = df.iloc[:, 0].values
    signal = df.iloc[:, 1].values
    return time, signal
