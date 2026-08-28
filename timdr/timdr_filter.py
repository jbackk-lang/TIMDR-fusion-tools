import numpy as np


def timdr(signal, window=64, drop_last=False):
    """
    TIMDR: redukcja informacji przez usrednianie sygnalu w kolejnych oknach.

    Dzieli sygnal na nie-nakladajace sie okna o rozmiarze `window` probek
    i zwraca srednia kazdego okna.

    Zachowanie ostatniego, niepelnego okna (gdy len(signal) nie jest
    wielokrotnoscia `window`):
      drop_last=False (domyslnie) - ostatnie, krotsze okno jest zachowane
        jako ostatni element wyniku. Wczesniej byl on po cichu odrzucany,
        co bezpowrotnie gubilo koncowke kazdego sygnalu, ktorego dlugosc
        nie byla wielokrotnoscia `window`, bez zadnego ostrzezenia.
      drop_last=True - przywraca stare zachowanie (odrzuca ostatnie
        niepelne okno), dla kompatybilnosci wstecznej.

    Parametry:
      signal    - sekwencja liczb.
      window    - rozmiar okna w probkach (domyslnie 64).
      drop_last - patrz wyzej (domyslnie False).

    Zwraca:
      np.ndarray srednich okien. Pusta tablica, jesli signal jest pusty.
    """
    x = np.asarray(signal, dtype=float)
    out = []
    for i in range(0, len(x), window):
        chunk = x[i:i + window]
        if len(chunk) == 0:
            break
        if len(chunk) < window and drop_last:
            break
        out.append(np.mean(chunk))
    return np.array(out)
