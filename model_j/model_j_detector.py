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


def sustained_drop_mask(signal, window=1250, drop_fraction=0.30):
    """
    Skala DLUGA mostu (patrz bridge_detector() nizej): flaguje probki, gdzie
    sygnal spadl o wiecej niz `drop_fraction` wzgledem swojego lokalnego
    szczytu w poprzedzajacym oknie `window` probek (bez zagladania w
    przyszlosc) - to POSUWANA, liczona w kazdym punkcie wersja JUZ
    zwalidowanego kryterium klasyfikacji TCABR z Zenodo (">30% spadku
    pradu wzgledem szczytu w oknie 5ms"), nie nowo wymyslona metryka.
    `window=1250` odpowiada 5ms przy probkowaniu 4us (dokladnie to samo
    okno co w oryginalnym kryterium), `drop_fraction=0.30` to dokladnie
    ten sam prog 30% - oba wybrane PRZED sprawdzeniem wyniku na
    jakimkolwiek konkretnym strzale, nie dobrane pod wynik.

    UWAGA: pierwsza proba przeksztalcenia tej idei w z-score (MAD na
    pelnym oknowanym przyrostie sygnalu) zawiodla - mediana przyrostu
    wychodzi dokladnie 0 (regulacja pradu plazmy trzyma go plasko przez
    wiekszosc probek), wiec MAD drastycznie nie docenia typowej skali
    aktywnych wahan gdzie indziej w przebiegu i kazde odejscie od 0
    dostaje absurdalnie wysoki z-score (tysiace falszywych wykryc).
    Dlatego ta funkcja NIE zwraca z-score, tylko bezposrednio te sama,
    juz zwalidowana, nie-znormalizowana metryke procentowa co oryginalne
    kryterium.

    Parametry:
      signal        - sekwencja liczb.
      window        - rozmiar okna wstecz (probki), domyslnie 1250 (5ms
                       przy 4us/probke).
      drop_fraction - prog wzglednego spadku od lokalnego szczytu
                       (domyslnie 0.30 = 30%).

    Zwraca:
      np.ndarray bool (ta sama dlugosc co signal).

    ZNANE OGRANICZENIE (znalezione przy testowaniu, nie ukryte): pojedynczy,
    izolowany, jednopróbkowy skok w gorę, po ktorym sygnal NATYCHMIAST
    wraca do poprzedniego poziomu, tez zostanie oflagowany - ten skok
    sam staje sie "lokalnym szczytem" dla rolling-max, a natychmiastowy
    powrot wyglada jak >30% spadek od niego. To rozne od prawdziwego,
    utrzymujacego sie zaniku pradu (gdzie szczyt jest szeroki, nie
    jednopróbkowy) - w praktyce na realnych danych TCABR nie byl to
    problem (patrz tests/test_real_tcabr.py), ale warto o tym wiedziec
    przy uzyciu na innych sygnalach z izolowanymi impulsami.
    """
    x = np.asarray(signal, dtype=float)
    if x.size == 0:
        return np.array([], dtype=bool)
    peak = pd.Series(x).rolling(window, min_periods=1).max().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        drop = (peak - x) / np.abs(peak)
    drop = np.nan_to_num(drop, nan=0.0, posinf=0.0, neginf=0.0)
    return drop > drop_fraction


def bridge_detector(
    signal,
    long_window=1250,
    drop_fraction=0.30,
    short_window=1001,
    short_threshold=5.0,
    exclude_start=2000,
):
    """
    "Most" laczacy dwie skale czasowe - odpowiedz na realny problem
    znaleziony przy realnych danych TCABR: sam krotki, punktowy
    gradient_zscore(window=short_window) (patrz wyzej) trafia 2 z 3
    prawdziwych zaklocen, ale z duzo falszywych wykryc w tle (patrz
    data/real/README.md); sama dluga skala (sustained_drop_mask())
    poprawnie identyfikuje WSZYSTKIE 3 zaklocenia (to jest juz
    zwalidowane kryterium 2 z Zenodo), ale sama w sobie nie jest
    "detektorem punktowym" - to prog na calym przebiegu, nieczuly na
    lokalizacje w czasie tak precyzyjnie jak z-score.

    Most: probka jest wykryciem tylko jesli OBIE skale sie zgadzaja
    (AND) - krotka skala daje precyzyjna lokalizacje w czasie, dluga
    skala odrzuca punktowe fluktuacje szumu, ktore nie sa czescia
    prawdziwego, utrzymujacego sie spadku.

    Uczciwy wynik na realnych danych TCABR (zweryfikowany w
    tests/test_real_tcabr.py, PRZED wyciagnieciem dodatkowych probek do
    dalszej walidacji - patrz data/real/README.md): dla WSZYSTKICH 3
    zaklocajacych strzalow (15569, 22201, 20316) 100% wykryc mostu miesci
    sie w +-10ms od prawdziwego, niezaleznie wyznaczonego czasu
    zaklocenia, skupionych w 1-2 wyraznych klastrach czasowych - duza
    poprawa wzgledem samej krotkiej skali (2/3, wieksze tlo szumu). Na
    strzalach normalnych most nadal daje falszywe wykrycia (nie jest to
    doskonaly klasyfikator) - w JEDNYM z 2 normalnych strzalow (36973)
    tworzy pojedynczy, porownywalny wielkoscia klaster jak przy
    prawdziwym zakloceniu, co jest uczciwie udokumentowanym
    ograniczeniem, nie przemilczane.

    Parametry:
      signal          - sekwencja liczb.
      long_window     - okno (probki) dla sustained_drop_mask() (domyslnie
                         1250 = 5ms przy 4us/probke).
      drop_fraction   - prog dla sustained_drop_mask() (domyslnie 0.30).
      short_window    - okno (probki) dla gradient_zscore() (domyslnie 1001).
      short_threshold - prog |z-score| dla krotkiej skali (domyslnie 5.0).
      exclude_start   - liczba poczatkowych probek do pominiecia (domyslnie
                         2000) - wyklucza artefakt digitizera na starcie
                         zapisu (patrz data/real/README.md), ktory inaczej
                         jest wykrywany przez obie skale naraz.

    Zwraca:
      np.ndarray z indeksami (int) probek wykrytych przez obie skale.
    """
    x = np.asarray(signal, dtype=float)
    if x.size == 0:
        return np.array([], dtype=int)

    long_mask = sustained_drop_mask(x, window=long_window, drop_fraction=drop_fraction)
    short_points = model_j(x, threshold=short_threshold, window=short_window)
    short_mask = np.zeros(x.size, dtype=bool)
    short_mask[short_points] = True

    bridge_mask = long_mask & short_mask
    if exclude_start > 0:
        bridge_mask[:exclude_start] = False
    return np.where(bridge_mask)[0]
