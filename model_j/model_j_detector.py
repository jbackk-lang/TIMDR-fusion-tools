import numpy as np


def gradient_zscore(signal):
    """
    Liczy gradient sygnalu i zwraca jego z-score ((grad - mean) / std) -
    dokladnie ta wartosc, ktorej prog uzywa model_j(). Wydzielone jako
    osobna funkcja, zeby byla JEDNA definicja z-score w repo (uzywana i
    przez model_j(), i przez panel histogramu w dashboardzie /api.py -
    ten sam wzorzec konsolidacji co latro()/latro_features()).

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

    Parametry:
      signal - sekwencja liczb.

    Zwraca:
      np.ndarray z-score (ta sama dlugosc co signal). Pusta tablica jesli
      signal jest pusty albo gradient jest stale plaski (patrz wyzej).
    """
    x = np.asarray(signal, dtype=float)
    if x.size == 0:
        return np.array([], dtype=float)
    grad = np.gradient(x)
    std = np.std(grad)
    # prog wzgledny: kilkadziesiat razy epsilon maszynowy razy skala
    # gradientu - lapie zarowno scisle zero, jak i szum zmiennoprzecinkowy
    # rzedu 1e-16 na idealnie liniowych/stalych sygnalach
    scale = max(float(np.max(np.abs(grad))), 1.0)
    flat_eps = 100 * np.finfo(float).eps * scale
    if std <= flat_eps:
        return np.array([], dtype=float)
    return (grad - np.mean(grad)) / std


def model_j(signal, threshold=2.0):
    """
    Model J: detekcja punktow skretu sygnalu przez z-score gradientu.

    Liczy gradient sygnalu, standaryzuje go (gradient_zscore(), patrz
    wyzej) i zwraca indeksy probek, gdzie |z| > threshold. Prog jest
    wzgledny do skali gradientu (patrz gradient_zscore()), nie sztywna
    stala liczba.

    Parametry:
      signal    - sekwencja liczb.
      threshold - prog |z-score| powyzej ktorego probka jest uznawana za
                  punkt skretu (domyslnie 2.0).

    Zwraca:
      np.ndarray z indeksami (int) punktow skretu. Pusta tablica jesli
      signal jest pusty albo gradient jest stale plaski.
    """
    z = gradient_zscore(signal)
    if z.size == 0:
        return np.array([], dtype=int)
    return np.where(np.abs(z) > threshold)[0]
