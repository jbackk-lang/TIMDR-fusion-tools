import numpy as np
import pandas as pd


def _estimate_quantization_step(signal):
    """
    Szacuje krok kwantyzacji ADC bezposrednio z WLASNYCH wartosci sygnalu
    (mediana odstepu miedzy kolejnymi, roznymi wartosciami po posortowaniu) -
    to fizyczna wlasciwosc instrumentu, mierzona raz z calego sygnalu, NIE
    dopasowywana do polozenia jakiegokolwiek konkretnego, znanego zdarzenia.
    Uzywana jako kalibrowana (nie zgadywana) podloga dla lokalnej normalizacji
    w gradient_zscore(window=...) - patrz tam.

    Zwraca 0.0 dla sygnalu z mniej niz 2 roznymi wartosciami (nie da sie
    oszacowac kroku).
    """
    x = np.asarray(signal, dtype=float)
    uniq = np.unique(x)
    diffs = np.diff(uniq)
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return 0.0
    return float(np.median(diffs))


def gradient_zscore(signal, window=None):
    """
    Liczy gradient sygnalu i zwraca jego z-score - dokladnie ta wartosc,
    ktorej prog uzywa model_j(). Wydzielone jako osobna funkcja, zeby byla
    JEDNA definicja z-score w repo (uzywana i przez model_j(), i przez
    panel histogramu w dashboardzie /api.py - ten sam wzorzec konsolidacji
    co latro()/latro_features()).

    Domyslnie (window=None): GLOBALNY z-score, ((grad - mean) / std)
    liczony raz na caly sygnal. Prosta, ale ma znana, udokumentowana wade
    na realnych danych (patrz data/real/README.md) - pojedynczy duzy,
    lokalny artefakt (np. skok digitizera na starcie zapisu) dominuje
    jedno globalne odchylenie standardowe i tlumi czulosc na reszcie
    przebiegu.

    Zabezpieczenie przed dzieleniem przez zero (tryb globalny): jesli
    gradient jest (albo numerycznie niemal jest) stala wartoscia -
    std(grad) == 0 dla sygnalu stalego, lub std(grad) rzedu bledu
    zmiennoprzecinkowego dla idealnie liniowego sygnalu (np.linspace daje
    std(grad) ~1e-16, nie dokladne 0) - zwraca pusta tablice zamiast po
    cichu:
      (a) dzielic przez scisle zero -> "RuntimeWarning: invalid value
          encountered in divide" i NaN (zweryfikowane na sygnale stalym:
          np.ones(50)), albo
      (b) dzielic przez std rzedu 1e-16, co wzmacnia szum
          zmiennoprzecinkowy do pozornie "duzych" z-score i daje falszywe
          wykrycia na sygnale, ktory w rzeczywistosci jest plaski
          (zweryfikowane na np.linspace(0, 10, 100): std(grad)=2.3e-16,
          bez tego zabezpieczenia dawalo to 5 falszywych detekcji).

    Opcjonalne window (int, probki): LOKALNA, przesuwna normalizacja
    (mediana/MAD gradientu w oknie przesuwnym o rozmiarze `window`,
    wysrodkowanym) zamiast jednej globalnej wartosci na caly sygnal -
    odporna na pojedynczy duzy artefakt (patrz wyzej), bo kazdy fragment
    przebiegu jest normalizowany wzgledem wlasnego, lokalnego tla, nie
    jednego wspolnego dla calosci.

    WAZNE zabezpieczenie w trybie lokalnym: na sygnalach z gruba
    kwantyzacja ADC (potwierdzone na realnych danych TCABR - patrz
    data/real/README.md, krok kwantyzacji IPlasma ~0.0745 kA, tylko
    ~1200 unikalnych wartosci na 45-50 tys. probek) lokalna mediana
    odchylenia bezwzglednego (MAD) gradientu w plaskich, skwantyzowanych
    oknach potrafi wyjsc (prawie) dokladnie zero, co przy dzieleniu daje
    bezsensowne z-score rzedu milionow zamiast realnej wartosci - to NIE
    jest to samo zabezpieczenie co w trybie globalnym (tam wystarczy eps
    wzgledny do skali, bo warunek jest globalny i rzadki; tutaj zdarza sie
    to w wielu oknach naraz). Podloga dla lokalnego MAD jest dlatego
    KALIBROWANA z fizycznej rozdzielczosci instrumentu
    (`_estimate_quantization_step()`, polowa oszacowanego kroku
    kwantyzacji) - mierzona raz z calego sygnalu, identycznie dla kazdego
    sygnalu, NIGDY z okna wokol konkretnego, znanego zdarzenia. To
    kalibracja pomiaru (fizyczna wlasciwosc instrumentu), nie dostrajanie
    progu pod z gory znany wynik.

    Parametry:
      signal - sekwencja liczb.
      window - opcjonalny rozmiar okna (int) dla trybu lokalnego. None
                (domyslnie) = tryb globalny.

    Zwraca:
      np.ndarray z-score (ta sama dlugosc co signal). Pusta tablica jesli
      signal jest pusty albo (w trybie globalnym) gradient jest stale
      plaski.
    """
    x = np.asarray(signal, dtype=float)
    if x.size == 0:
        return np.array([], dtype=float)
    grad = np.gradient(x)

    if window is None:
        std = np.std(grad)
        # prog wzgledny: kilkadziesiat razy epsilon maszynowy razy skala
        # gradientu - lapie zarowno scisle zero, jak i szum
        # zmiennoprzecinkowy rzedu 1e-16 na idealnie liniowych/stalych
        # sygnalach
        scale = max(float(np.max(np.abs(grad))), 1.0)
        flat_eps = 100 * np.finfo(float).eps * scale
        if std <= flat_eps:
            return np.array([], dtype=float)
        return (grad - np.mean(grad)) / std

    s = pd.Series(grad)
    min_periods = max(4, window // 4)
    med = s.rolling(window, center=True, min_periods=min_periods).median()
    mad = (s - med).abs().rolling(window, center=True, min_periods=min_periods).median()
    robust_std = mad * 1.4826  # skaluje MAD do odpowiednika std dla rozkladu normalnego
    quant_step = _estimate_quantization_step(x)
    floor = 0.5 * quant_step
    if floor > 0:
        robust_std = robust_std.clip(lower=floor)
    z = (s - med) / robust_std
    return z.fillna(0.0).to_numpy()


def model_j(signal, threshold=2.0, window=None):
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
      window    - opcjonalny rozmiar okna (int) dla lokalnej normalizacji
                  zamiast globalnej - patrz gradient_zscore().

    Zwraca:
      np.ndarray z indeksami (int) punktow skretu. Pusta tablica jesli
      signal jest pusty albo (w trybie globalnym) gradient jest stale
      plaski.
    """
    z = gradient_zscore(signal, window=window)
    if z.size == 0:
        return np.array([], dtype=int)
    return np.where(np.abs(z) > threshold)[0]
