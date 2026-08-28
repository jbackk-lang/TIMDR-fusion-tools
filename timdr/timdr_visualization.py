import numpy as np
import matplotlib.pyplot as plt


def plot_timdr(original, reduced, window=64, time=None):
    """
    Rysuje sygnal oryginalny i zredukowany (TIMDR) na wspolnej,
    poprawnie wyskalowanej osi X.

    Wczesniej `reduced` (wyjscie timdr(original, window=window), a wiec
    zdownsamplowane w przyblizeniu `window`-krotnie) bylo rysowane po
    prostu na tych samych indeksach probek co `original`. Dla original o
    dlugosci 640 i window=64, reduced ma dlugosc 10 - bez korekty zajmowal
    on wizualnie tylko pierwsze ~1.5% osi X zamiast rozciagac sie na cala
    dlugosc sygnalu, co dawalo mylacy wykres.

    Ta wersja skaluje os X dla `reduced` tak, aby kazdy jego punkt byl
    umieszczony w srodku okna probek, z ktorego zostal usredniony.

    Parametry:
      original - surowy sygnal (dlugosc n).
      reduced  - wyjscie timdr(original, window=window).
      window   - rozmiar okna uzyty przy wywolaniu timdr() (musi byc taki
                 sam, w przeciwnym razie os X bedzie bledna).
      time     - opcjonalna os czasu/indeksow dla `original` (domyslnie
                 indeksy probek 0..n-1). Zaklada rownomierne probkowanie.
    """
    n = len(original)
    if time is not None:
        t = np.asarray(time, dtype=float)
        dt = (t[-1] - t[0]) / max(n - 1, 1) if n > 1 else 1.0
        orig_x = t
        t0 = t[0]
    else:
        dt = 1.0
        orig_x = np.arange(n)
        t0 = 0.0

    reduced_x = t0 + (np.arange(len(reduced)) + 0.5) * window * dt

    plt.figure(figsize=(12, 5))
    plt.plot(orig_x, original, label="Oryginal", alpha=0.5)
    plt.plot(reduced_x, reduced, label="TIMDR", linewidth=2, marker="o")
    plt.legend()
    plt.title("TIMDR - redukcja informacji")
    plt.xlabel("czas" if time is not None else "probka")
    plt.ylabel("wartosc")
    plt.grid(True)
    plt.show()
