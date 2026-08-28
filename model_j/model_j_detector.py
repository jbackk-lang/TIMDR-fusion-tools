import numpy as np


def model_j(signal, threshold=2.0):
    """
    Model J: detekcja punktow skretu sygnalu przez z-score gradientu.

    Liczy gradient sygnalu, standaryzuje go ((grad - mean) / std) i zwraca
    indeksy probek, gdzie |z| > threshold.

    Zabezpieczenie przed dzieleniem przez zero: jesli gradient jest (albo
    numerycznie niemal jest) stala wartoscia - std(grad) == 0 dla sygnalu
    stalego, lub std(grad) rzedu bledu zmiennoprzecinkowego dla idealnie
    liniowego sygnalu (np.linspace daje std(grad) ~1e-16, nie dokladne 0)
    - zwraca pusta tablice zamiast po cichu:
      (a) dzielic przez scisle zero -> "RuntimeWarning: invalid value
          encountered in divide" i NaN (zweryfikowane na sygnale stalym:
          np.ones(50)), albo
      (b) dzielic przez std rzedu 1e-16, co wzmacnia szum
          zmiennoprzecinkowy do pozornie "duzych" z-score i daje falszywe
          wykrycia na sygnale, ktory w rzeczywistosci jest plaski
          (zweryfikowane na np.linspace(0, 10, 100): std(grad)=2.3e-16,
          bez tego zabezpieczenia dawalo to 5 falszywych detekcji).
    Prog jest wzgledny do skali gradientu, nie sztywna stala liczba.

    Parametry:
      signal    - sekwencja liczb.
      threshold - prog |z-score| powyzej ktorego probka jest uznawana za
                  punkt skretu (domyslnie 2.0).

    Zwraca:
      np.ndarray z indeksami (int) punktow skretu. Pusta tablica jesli
      signal jest pusty albo gradient jest stale plaski.
    """
    x = np.asarray(signal, dtype=float)
    if x.size == 0:
        return np.array([], dtype=int)
    grad = np.gradient(x)
    std = np.std(grad)
    # prog wzgledny: kilkadziesiat razy epsilon maszynowy razy skala
    # gradientu - lapie zarowno scisle zero, jak i szum zmiennoprzecinkowy
    # rzedu 1e-16 na idealnie liniowych/stalych sygnalach
    scale = max(float(np.max(np.abs(grad))), 1.0)
    flat_eps = 100 * np.finfo(float).eps * scale
    if std <= flat_eps:
        return np.array([], dtype=int)
    z = (grad - np.mean(grad)) / std
    return np.where(np.abs(z) > threshold)[0]
