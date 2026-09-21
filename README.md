# fusion-tools

**Klasyfikator zakłóceń plazmy (TCABR)** zbudowany i zwalidowany na
realnych danych, plus ogólny toolkit do analizy sygnałów z diagnostyki
plazmy (W7-X, JET, DIII-D, EAST) oparty na TIMDR (redukcja informacji),
Λ-τ-ρ (metryki strukturalne sygnału) oraz Model J (detekcja punktów
skrętu) — narzędzia, na których klasyfikator jest zbudowany.

---

## Klasyfikacja zakłóceń TCABR — wynik

Trzy niezależne metody, każda zbudowana na oryginalnym (małym) zbiorze
danych z parametrami zamrożonymi PRZED zobraniem kolejnych, wcześniej
niewidzianych strzałów — i każda faktycznie sprawdzona na tych nowych
danych, nie tylko na tych, na których powstała. Pełny opis, wszystkie
odrzucone próby i uczciwe ograniczenia: [`data/real/README.md`](data/real/README.md).

| metoda | co robi | wynik held-out (nowe, wcześniej niewidziane strzały) |
|---|---|---|
| `is_fast_quench()` (kształt zaniku, `model_j/model_j_detector.py`) | **Klasyfikuje** zakłócający vs. normalny strzał po czasie zaniku prądu po szczycie | **19/19 (100%)** na 19 nowych strzałach — 0 błędów |
| `phasespace_funnel_ratio()` (portret fazowy I,V) | **Klasyfikuje** po tym, czy trajektoria (prąd, napięcie) rozszerza się czy nie | **12/14 (86%) czułość, 5/5 (100%) swoistość** na tych samych 19 nowych strzałach |
| `bridge_detector()` (dwie skale czasowe) | **Lokalizuje** już znane zakłócenie w czasie (nie odróżnia zakłócenia od normalnego strzału) | **100% precyzji lokalizacji** na 3 oryginalnych, **80% pełny sukces / 96,8% średnia precyzja** na 30 nowych |

Na pełnym, połączonym zbiorze **54 realnych strzałów TCABR** (37
zakłócających + 17 normalnych, 162 sygnały): `is_fast_quench()`
poprawnie klasyfikuje 36/37 zakłócających (jeden udokumentowany,
nienaprawiony wyjątek — strzał 21918, nietypowo wolne zakłócenie) i
17/17 normalnych.

**Uczciwe zastrzeżenie**: `is_fast_quench()`/`phasespace_funnel_ratio()`
odróżniają zakłócający strzał od normalnego (klasyfikacja). `bridge_detector()`
lokalizuje zakłócenie W CZASIE, gdy już wiadomo, że tam jest — to inne
zadanie, nie gotowy klasyfikator. Obie klasy metod uzupełniają się, nie
zastępują.

Wynik widoczny live w dashboardzie (panel "Detektor geometryczny" — patrz
niżej) dla dowolnego scenariusza TCABR.

### Walidacja cross-device na MAST (bez etykiet)

`is_fast_quench()`/`quench_duration()` uruchomione bez zmian kodu na dwóch
rozłącznych próbkach po 579 strzałów MAST (`magnetics/ip`, parametry
okienkowe przeliczone na czas fizyczny, kryteria zamrożone przed
uruchomieniem): rozkład czasu zaniku jest dwumodalny (ok. 2–3 ms i ok.
50 ms, przerwa 4–15 ms zawiera ok. 4,5% strzałów) i powtarzalny w obu
próbkach; próg 15 ms z TCABR działa tak samo jak 7,7 ms. **To opis struktury
rozkładu, nie trafność klasyfikacji** — dla MAST nie ma dostępnych etykiet
dysrupcji (`level2/defuse`: AccessDenied), więc nie wiadomo, czy szybki tryb
(ok. 65% strzałów) to zakłócenia. `bridge_detector()` nie wykazał na MAST
związku z `is_fast_quench()`. Pre-rejestracje, skrypty i wyniki:
[`data/mast_cross_device/`](data/mast_cross_device/).

---

## Cele projektu

- **klasyfikacja/detekcja zakłóceń plazmy na realnych danych TCABR**
  (patrz wyżej) — flagowy, zwalidowany wynik tego repozytorium,
- redukcja szumu i nadmiarowości sygnałów z diagnostyk plazmy (TIMDR),
- ekstrakcja prostych cech strukturalnych sygnału (Λ-τ-ρ),
- detekcja punktów skrętu / gwałtownych zmian dynamiki (Model J) — baza,
  na której zbudowane są `bridge_detector()`/`quench_duration()`/
  `phasespace_funnel_ratio()` wyżej,
- wczytywanie danych w formatach używanych w fuzji (CSV, HDF5, MDSplus).

Domyślny przykładowy sygnał (`data/w7x_mirnov_example.csv`) jest
syntetyczny. Realne dane TCABR — patrz sekcja "Realne dane (TCABR)" niżej
i [`data/real/README.md`](data/real/README.md) po pełny opis.

---

## Struktura

```
fusion-tools/
├── data/                       # przykładowy syntetyczny sygnał + metadane
│   ├── w7x_mirnov_example.csv
│   ├── w7x_mirnov_example.h5   # to samo co CSV, jako HDF5 (datasety "time"/"signal")
│   ├── example_metadata.json
│   └── real/                   # realne dane (TCABR) — patrz niżej
├── parsers/                    # wczytywanie danych: CSV, HDF5, MDSplus
│   ├── csv_parser.py
│   ├── hdf5_parser.py
│   └── mdsplus_parser.py
├── timdr/                      # redukcja informacji + wizualizacja
│   ├── timdr_filter.py
│   └── timdr_visualization.py
├── latro/                      # metryki strukturalne Λ-τ-ρ
│   ├── latro_core.py
│   └── latro_features.py
├── model_j/                    # detekcja punktów skrętu + klasyfikator zakłóceń TCABR
│   └── model_j_detector.py
├── demo/                       # scenariusze demo + działające demo (skrypt + notebook)
│   ├── scenarios.py
│   ├── run_demo.py
│   └── fusion_demo.ipynb
├── api.py                      # FastAPI backend dla dashboardu
├── static/                     # dashboard (Chart.js zvendorowany lokalnie w static/vendor/)
├── run.bat                     # launcher dla Windows (venv + pip + uvicorn)
├── tests/                      # pytest
└── requirements.txt
```

`parsers/`, `timdr/`, `latro/`, `model_j/` to "namespace packages" Pythona 3
(bez `__init__.py`) — importy działają, jeśli uruchamiasz kod z katalogu
głównego repo, np. `from timdr.timdr_filter import timdr`.

---

## Instalacja

```bash
pip install -r requirements.txt
```

`MDSplus` jest w `requirements.txt` zakomentowany — jest to opcjonalna,
specjalistyczna zależność potrzebna wyłącznie do `parsers/mdsplus_parser.py`
(połączenie z serwerem MDSplus tokamaka/stellaratora). Nie jest wymagana do
pracy z CSV/HDF5 ani do żadnego innego modułu. Ten parser nie był testowany
w tym repozytorium (brak dostępu do serwera MDSplus w środowisku
deweloperskim).

---

## Dashboard

Webowy dashboard (FastAPI + Chart.js, zvendorowany lokalnie w
`static/vendor/` — działa bez internetu) nad tym samym pipeline'em, z
wyborem scenariusza demo, wgrywaniem własnego pliku (CSV lub HDF5), albo
realnych danych TCABR — w tym panelem klasyfikatora zakłóceń.

**Windows:** dwuklik na `run.bat` — tworzy `.venv`, instaluje zależności,
startuje serwer i otwiera przeglądarkę.

**Ręcznie (dowolny system):**

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

- dashboard: `http://127.0.0.1:8000/`
- dokumentacja Swagger: `http://127.0.0.1:8000/docs`

Co pokazuje dashboard:

1. **Wykres sygnału** — oryginał razem ze zredukowanym TIMDR (na wspólnej,
   poprawnie wyskalowanej osi czasu) i zaznaczonymi punktami skrętu
   Modelu J.
2. **Dryf Λ-τ-ρ** — drugi wykres (słupkowy), pokazujący Λ, τ, ρ liczone
   **osobno w każdym kolejnym oknie** (`latro_windowed()` w
   `latro_core.py`, ten sam podział na okna co `timdr()`), zamiast jednej
   uśrednionej wartości na cały sygnał. Pozwala zobaczyć, czy i gdzie
   energia/rozrzut sygnału się zmienia w czasie.
3. **Widmo częstotliwości (FFT)** — amplituda w funkcji częstotliwości
   (`np.fft.rfft`, bez składowej DC), liczona po stronie serwera
   (`_fft_spectrum()` w `api.py`). Przydatne do zobaczenia oscylacji/modów,
   które na surowym przebiegu czasowym mogą być słabo widoczne.
4. **Histogram z-score gradientu** — rozkład dokładnie tej wartości, którą
   progowuje Model J (`gradient_zscore()`, patrz niżej) — pokazuje GDZIE
   próg faktycznie "odcina" rozkład, nie tylko finalną liczbę wykryć.
5. **Detektor geometryczny (kształt zaniku)** — wynik `is_fast_quench()`/
   `quench_duration()` (klasyfikacja: szybki/wolny zanik) oraz, gdy
   dostępny jest siostrzany kanał VLoop, `phasespace_funnel_ratio()`
   (portret fazowy I,V) — patrz "Klasyfikacja zakłóceń TCABR" wyżej.
6. **Opis wyniku** — krótki, deterministyczny opis po polsku generowany z
   policzonych statystyk (bez wywołania LLM): liczba próbek i redukcja,
   zakres wartości, liczba wykrytych punktów Modelu J pogrupowana w
   odrębne zdarzenia w czasie, oraz kierunek zmiany energii (ρ) między
   początkiem a końcem sygnału. Kończy się zastrzeżeniem, że to opis
   statystyczny, nie interpretacja fizyczna MHD.
7. **Porównanie scenariuszy demo** — osobny panel, który uruchamia
   Λ-τ-ρ i Model J na WSZYSTKICH scenariuszach demo naraz (ten sam
   window/threshold z formularza) i pokazuje wynik jako wykres słupkowy
   (liczba punktów Modelu J) plus tabelę (`GET /scenarios/compare`).

### Scenariusze demo

Dashboard ma selektor scenariuszy zamiast jednego wbudowanego sygnału
(`demo/scenarios.py`, `GET /scenarios`). Pięć jest **syntetycznych**:

| id | Co pokazuje |
|---|---|
| `baseline` | Domyślny przykład: 2 sinusoidy + 3 wstrzyknięte zdarzenia (`data/w7x_mirnov_example.csv`). |
| `quiet` | Kontrolka negatywna: prawie płaski sygnał, zero wstrzykniętych zdarzeń. |
| `single_burst` | Cichy sygnał + jedno silne, izolowane zdarzenie. |
| `growing_mode` | Oscylacja o amplitudzie rosnącej wykładniczo (dobry przykład na wykres dryfu ρ). |
| `noisy_flat` | Sam szum, większa amplituda niż `quiet`, zero struktury. |

Kolejnych 162 to realne dane TCABR (`tcabr_<shot>_<kanał>`, 54 strzały ×
3 kanały) — patrz sekcja "Realne dane (TCABR)" niżej.

**Obserwacja z panelu porównania**: przy domyślnym progu 2.0 `quiet` (sam
szum, ZERO prawdziwych zdarzeń) daje ok. 90-100 "wykryć" Modelu J na 2000
próbek — to statystyczny efekt progowania z-score na czystym szumie
(oczekiwane ~4.5% przy |z|>2), nie błąd. `single_burst` (JEDNO prawdziwe,
silne zdarzenie) daje ich zaskakująco MNIEJ (~13), bo pojedynczy duży
skok podbija odchylenie standardowe gradientu użyte do normalizacji
z-score, co tłumi detekcje szumu tła gdzie indziej w tym samym sygnale.
Wniosek: surowa liczba wykryć Modelu J bez takiego kontekstu nic nie mówi
o tym, czy sygnał ma prawdziwą strukturę — patrz
`tests/test_api.py::test_scenarios_compare_endpoint_returns_all_scenarios`.

Panel ma też przycisk "Anuluj" (`AbortController` po stronie przeglądarki
+ limit rozmiaru sygnału po stronie serwera — `MAX_SAMPLES = 200 000` w
`api.py` — żeby duży plik nie zawiesił karty przeglądarki).

**Wgrywanie HDF5:** HDF5 nie ma ustalonej konwencji "pierwsza kolumna to
czas" jak CSV, więc `api.py` szuka datasetów nazwanych `time`/`t`/`czas`
(oś X) i `signal`/`value`/`data`/... (sygnał); jeśli nazwy nie pasują, a
jest dokładnie jeden pozostały 1D numeryczny dataset, używa go bez
pytania; przy kilku kandydatach wybiera pierwszy alfabetycznie, ale **nie
robi tego po cichu** — odpowiedź `/analyze` zawsze zawiera `hdf5_info` z
pełną listą dostępnych datasetów i flagą `ambiguous`, a dashboard pokazuje
to w żółtym pasku pod przyciskami. Wybór można wymusić polem "Dataset
HDF5" (parametr `dataset` w API). Do testów jest w repo gotowy
`data/w7x_mirnov_example.h5` (ten sam sygnał co CSV, datasety `time` i
`signal`) — dashboard ma link do jego pobrania.

Endpointy API:

| Endpoint | Metoda | Opis |
|---|---|---|
| `/` | GET | dashboard |
| `/example` | GET | metadane wbudowanego przykładowego sygnału |
| `/analyze` | POST | uruchamia pipeline; pola formularza: `file` (CSV lub HDF5, opcjonalny), `scenario` (id z `/scenarios`, używany gdy nie wgrano pliku), `use_example` (bool, alias na scenariusz `baseline`), `window`, `threshold`, `drop_last`, `dataset` (nazwa datasetu HDF5, opcjonalna) |
| `/scenarios` | GET | lista dostępnych scenariuszy demo (`id`, `label`, `description`) |
| `/scenarios/compare` | GET | Λ-τ-ρ i liczba punktów Modelu J dla wszystkich scenariuszy naraz (parametry `window`, `threshold`) |
| `/data/...` | GET | statyczny dostęp do plików w `data/` (np. pobranie przykładowego `.h5`) |

Odpowiedź `/analyze` zawiera dodatkowo: `latro_windowed` (`{x, lambda,
tau, rho}` per okno), `spectrum` (`{freq, magnitude}`, FFT bez składowej
DC), `model_j_zscore_hist` (`{bin_edges, counts, is_flat, threshold}`),
`geometric` (`{quench_duration_s, is_fast_quench, funnel_ratio,
funnel_ratio_note}` — wynik klasyfikatora zakłóceń, patrz wyżej),
`description` (opis tekstowy), `scenario` (metadane wybranego scenariusza
demo — tylko gdy nie wgrano pliku) oraz — tylko dla wgranego HDF5 —
`hdf5_info` (`available_datasets`, `signal_dataset`, `time_dataset`,
`time_source`, `ambiguous`).

---

## Moduły

### `parsers/`

| Funkcja | Plik | Uwagi |
|---|---|---|
| `load_csv(path)` | `csv_parser.py` | plik CSV, 2 kolumny: czas, wartość |
| `load_hdf5(path)` | `hdf5_parser.py` | zwraca `dict` wszystkich datasetów w pliku |
| `load_mdsplus(server, tree, shot, signal)` | `mdsplus_parser.py` | wymaga zainstalowanego pakietu `MDSplus`, nieprzetestowane |

### `timdr/`

`timdr(signal, window=64, drop_last=False)` — dzieli sygnał na
nienakładające się okna po `window` próbek i zwraca średnią każdego okna.
Domyślnie zachowuje ostatnie, niepełne okno jako krótszy ostatni element
wyniku. `drop_last=True` odrzuca je zamiast tego.

`plot_timdr(original, reduced, window=64, time=None)` — rysuje sygnał
oryginalny i zredukowany na wspólnej, poprawnie wyskalowanej osi X.

### `latro/`

`latro(signal)` z `latro_core.py` — **jedyna** definicja Λ-τ-ρ w tym repo:

- **Λ (lambda)** — amplituda zakresu sygnału: `max(signal) - min(signal)`
- **τ (tau)** — średnia wartość bezwzględna: `mean(|signal|)`
- **ρ (rho)** — energia sygnału (średnia moc): `mean(signal**2)`

To proste, opisowe metryki statystyczne w dziedzinie czasu — nie modelują
fizycznej "transformacji" ani "defektu" w jakimś silniejszym sensie. Nazwy
Λ/τ/ρ pochodzą z terminologii projektu GIA-TIMDR.

`latro_features(signal)` z `latro_features.py` zwraca to samo jako `dict`
(`{"lambda": ..., "tau": ..., "rho": ...}`) — cienki wrapper nad `latro()`,
żeby była jedna definicja, nie dwie osobne do rozjechania się.

`latro_windowed(signal, window=64, drop_last=False)` — liczy `latro()`
osobno dla każdego kolejnego okna sygnału (ten sam podział na okna co
`timdr()`), zamiast jednej uśrednionej trójki na cały sygnał. Zwraca
`(lambdas, taus, rhos)` — trzy tablice, po jednej wartości na okno. Do
tego, żeby zobaczyć jak Λ-τ-ρ **zmieniają się w czasie**, nie tylko ich
średnią (używane przez dashboard do wykresu "dryfu").

### `model_j/` — detekcja punktów skrętu i klasyfikator zakłóceń TCABR

`gradient_zscore(signal)` — liczy gradient sygnału i zwraca jego z-score
(`(grad - mean) / std`), z zabezpieczeniem przed dzieleniem przez zero
(albo przez bardzo małą liczbę rzędu szumu zmiennoprzecinkowego) dla
sygnału stałego lub idealnie liniowego — zwraca wtedy pustą tablicę
zamiast fałszywych detekcji. Jedyna definicja z-score w repo — używana i
przez `model_j()`, i przez histogram w dashboardzie.

`model_j(signal, threshold=2.0, window=None)` — cienki wrapper nad
`gradient_zscore()`: zwraca indeksy próbek, gdzie `|z| > threshold`. To
detektor lokalnych, gwałtownych zmian gradientu ("punktów skrętu"), a nie
detektor lokalnych maksimów.

Opcjonalny `window` (liczba próbek) przełącza `gradient_zscore()` z
normalizacji globalnej (domyślnej, jedna wartość na cały sygnał) na
lokalną, przesuwną (mediana/MAD gradientu w oknie) — odporną na
pojedynczy duży, lokalny artefakt, który w trybie globalnym potrafi
zdominować całą normalizację. Podłoga dla lokalnego MAD jest kalibrowana
z własnego kroku kwantyzacji ADC sygnału (`_estimate_quantization_step()`)
zamiast dobierana ręcznie — sam ten tryb daje na realnych danych TCABR
wynik częściowy (2 z 3 realnych zakłóceń, nie 3 z 3).

`sustained_drop_mask(signal, window=1250, drop_fraction=0.30)` — inna,
"długa" skala: flaguje próbki, gdzie sygnał spadł o więcej niż
`drop_fraction` względem swojego lokalnego szczytu w oknie `window` —
przesuwna wersja już zwalidowanego kryterium klasyfikacji TCABR z Zenodo
(>30% spadku w oknie 5ms), nie nowa metryka.

`bridge_detector(signal, long_window=1250, drop_fraction=0.30, short_window=1001, short_threshold=5.0, exclude_start=2000)` —
"most" łączący obie skale: próbka jest wykryciem tylko, gdy ZGADZAJĄ SIĘ
OBIE (`gradient_zscore(window=short_window)` ORAZ `sustained_drop_mask()`
naraz). Krótka skala daje precyzyjną lokalizację w czasie, długa
odrzuca punktowe fluktuacje szumu, które nie są częścią prawdziwego,
utrzymującego się spadku. **Lokalizuje zakłócenie w czasie, nie
klasyfikuje strzału** (patrz "Klasyfikacja zakłóceń TCABR" wyżej) — 100%
precyzji lokalizacji na oryginalnych 3 zakłócających strzałach, 80% pełny
sukces / 96,8% średnia precyzja na 30 nowych, wcześniej niewidzianych.

`quench_duration(signal, dt=1.0, fraction_high=0.70, fraction_low=0.10, smooth_window=51, exclude_start=0)` —
GEOMETRYCZNA cecha: czas (w jednostkach `dt`), w jakim WYGŁADZONY sygnał
(średnia ruchoma) opada od 70% do 10% swojej wartości szczytowej po
`exclude_start`. Zwraca `None`, gdy któryś próg nie zostanie przekroczony.

`is_fast_quench(signal, dt=1.0, duration_threshold=0.015, **kwargs)` —
**klasyfikator** oparty na `quench_duration()` (próg 15ms wyznaczony
wprost z przerwy między zaobserwowanymi zakresami, nie dopasowany do
żadnego przypadku). Na 54 realnych strzałach TCABR (35 oryginalnych + 19
held-out): 36/37 zakłócających poprawnie `True` (jeden udokumentowany
wyjątek, strzał 21918 — nietypowo wolne zakłócenie, ~27,6ms), 17/17
normalnych poprawnie `False`. Na samych 19 held-out: **19/19, bez ani
jednej pomyłki**.

`phasespace_funnel_ratio(primary_signal, secondary_signal, exclude_start=2000, smooth_window=51, fraction_high=0.70, fraction_low=0.10, edge_fraction=0.10)` —
**klasyfikator** oparty na portrecie fazowym dwóch kanałów (np. IPlasma +
VLoop, fizycznie uzasadnione przez V≈L·dI/dt): stosunek promienia
trajektorii (I,V) względem jej centroidu na końcu vs. początku okna
zaniku. Znaleziony eksploracyjnie na oryginalnych 35 strzałach, następnie
**faktycznie zwalidowany held-out** na 19 nowych: 12/14 (86%) czułość,
5/5 (100%) swoistość, próg 1.65. Mniejsza podstawa dowodowa niż
`is_fast_quench()` (jedna runda walidacji held-out) — status i pełne
zastrzeżenia w [`data/real/README.md`](data/real/README.md).

Pełny opis wszystkich metod, odrzuconych prób i uczciwych ograniczeń:
[`data/real/README.md`](data/real/README.md).

---

## Demo

Przykładowy sygnał `data/w7x_mirnov_example.csv` jest **syntetyczny**:
suma dwóch sinusoid + szum + 3 wstrzyknięte gwałtowne zdarzenia w próbkach
400, 950, 1600 (dokładny przepis generowania w
`data/example_metadata.json`). Nazwa nawiązuje do sygnału z cewki Mirnova
wyłącznie dla ilustracji — to nie są dane z żadnego prawdziwego urządzenia.

Uruchomienie:

```bash
python demo/run_demo.py
```

albo interaktywnie: `demo/fusion_demo.ipynb`.

Kod demo używa bezpośrednio funkcji bibliotecznych (nie ich reimplementacji
w komentarzach) — to samo, co jest w `timdr/`, `latro/`, `model_j/`.

---

## Przykład użycia

```python
from parsers.csv_parser import load_csv
from timdr.timdr_filter import timdr
from latro.latro_core import latro
from model_j.model_j_detector import model_j, is_fast_quench

time, signal = load_csv("data/w7x_mirnov_example.csv")

reduced = timdr(signal, window=64)
lam, tau, rho = latro(signal)
points = model_j(signal, threshold=2.0)

print("Λ-τ-ρ:", lam, tau, rho)
print("Punkty Modelu J:", list(points)[:10])

# Klasyfikacja zakłóceń na realnym sygnale TCABR (IPlasma) - patrz
# data/real/README.md po dt/exclude_start uzywane przy walidacji:
# dt_sample = t[1] - t[0]
# is_fast_quench(signal, dt=dt_sample, duration_threshold=0.015, exclude_start=2000)
```

---

## Testy

```bash
pytest tests/ -v
```

Testy obejmują: poprawność `latro()`/`latro_features()`/`latro_windowed()`,
zabezpieczenie `model_j()`/`gradient_zscore()` przed dzieleniem przez
zero, zachowanie ostatniego niepełnego okna w `timdr()`, wczytywanie CSV,
pełny pipeline end-to-end na przykładowym sygnale (sprawdza, że Model J
faktycznie wykrywa 3 wstrzyknięte zdarzenia), endpointy API
(`tests/test_api.py` — `/analyze` na przykładzie/scenariuszu/wgranym
CSV/HDF5, limit rozmiaru, odrzucanie nieobsługiwanych rozszerzeń,
obecność `latro_windowed`/`spectrum`/`model_j_zscore_hist`/`geometric`/
`description` w odpowiedzi), scenariusze demo (`tests/test_scenarios.py`),
oraz — jeśli lokalnie obecne realne dane TCABR —
`tests/test_real_tcabr.py` (globalny, lokalny/skalibrowany i mostowy tryb
Modelu J na realnych sygnałach, plus zgodność CSV-ów z surowymi `.npz`),
`tests/test_real_tcabr_batch2.py` (niezależna walidacja mostu na 30
wcześniej niewidzianych strzałach), `tests/test_real_tcabr_quench_duration.py`
(walidacja `quench_duration()`/`is_fast_quench()` na wszystkich 54
realnych strzałach), `tests/test_real_tcabr_phasespace.py` (walidacja
`phasespace_funnel_ratio()` na tych samych 54) oraz
`tests/test_real_tcabr_batch3_geometric.py` (jawna, held-out walidacja
OBU klasyfikatorów geometrycznych na 19 najnowszych, wcześniej
niewidzianych strzałach, w tym regresyjny test bit-exact CSV-ów tej
partii — patrz `data/real/raw/` i `data/real/README.md` niżej).
**469/469** testów przechodzi z danymi TCABR obecnymi lokalnie,
**86/86** bez nich (59 pominiętych) — część testów jest sparametryzowana
po liście scenariuszy demo, która rośnie z 5 (same syntetyczne) do 167
(+ 162 realnych TCABR), stąd różnica większa niż tylko same testy w
`test_real_tcabr*.py`.

---

## Realne dane (TCABR)

`data/real/` zawiera 162 PRAWDZIWE sygnały (54 wyładowania × 3 kanały —
`IPlasma`, `VLoop`, `BbMirnovN01`) z tokamaka TCABR (Zenodo, DOI
10.5281/zenodo.21843354, CC-BY 4.0), widoczne w dashboardzie jako
scenariusze `tcabr_<shot>_<kanał>` obok syntetycznych. 37 wyładowań jest
zakłócających (z niezależnie wyznaczonym czasem zakłócenia), 17 normalnych,
zebranych w czterech partiach (patrz [`data/real/README.md`](data/real/README.md)
po pełną tabelę i historię).

**Trzy tryby Modelu J (lokalizacja, nie klasyfikacja)**: w domyślnym,
**globalnym** trybie (`gradient_zscore()`, jedna normalizacja na cały
przebieg) Model J **nie wykrywa żadnego** z prawdziwych zdarzeń
zakłóceniowych — artefakt digitizera na starcie zapisu dominuje globalne
odchylenie standardowe gradientu. W **lokalnym, skalibrowanym** trybie
(`window=1001`) wynik jest częściowy (2 z 3 pierwszych strzałów). W
trybie **mostowym** (`bridge_detector()`) zbudowanym na pierwszych 5
strzałach: 100% precyzji lokalizacji na wszystkich 3, zwalidowane na 30
nowych (80% pełny sukces / 96,8% średnia precyzja) — ale to lokalizacja
W CZASIE już znanego zakłócenia, nie klasyfikacja "czy to zakłócenie".

**Klasyfikacja (`is_fast_quench()`/`phasespace_funnel_ratio()`)** — patrz
sekcja "Klasyfikacja zakłóceń TCABR" na górze tego pliku po pełne liczby.
Pełny, szczegółowy opis wszystkich metod, odrzuconych prób i wyniku
walidacji w [`data/real/README.md`](data/real/README.md).

---

## Zakres i ograniczenia

- `parsers/mdsplus_parser.py` nie był uruchamiany przeciw prawdziwemu
  serwerowi MDSplus w tym środowisku — API wygląda poprawnie, ale jest
  nieprzetestowane empirycznie.
- Λ-τ-ρ i Model J to proste metryki/detektory statystyczne w dziedzinie
  czasu, nie zwalidowany model fizyczny MHD. Interpretacje w rodzaju
  "punkty skrętu = wczesne wykrywanie ELM/sawtooth" są hipotezami do
  zweryfikowania na prawdziwych danych, nie potwierdzonym wynikiem.
  "Opis wyniku" w dashboardzie to czysto statystyczne podsumowanie
  (liczby, zakresy, trend) — nie diagnoza plazmy.
- `is_fast_quench()` ma jeden udokumentowany, nienaprawiony wyjątek
  (strzał 21918) — nie jest to klasyfikator ze 100% skutecznością na
  wszystkich znanych przypadkach.
- `phasespace_funnel_ratio()` ma mniejszą podstawę dowodową niż
  `is_fast_quench()`/`bridge_detector()` (jedna runda walidacji held-out,
  19 strzałów) i nie jest doskonały (2 fałszywie ujemne na tej rundzie).
- Walidacja na MAST (`data/mast_cross_device/`) nie ma etykiet dysrupcji:
  pokazuje powtarzalną dwumodalność czasu zaniku, nie skuteczność
  klasyfikacji na MAST. `phasespace_funnel_ratio()` nie był na MAST
  testowany (Vloop z rekonstrukcji EFIT ma zbyt rzadkie próbkowanie, 5 ms,
  z lukami).
- Wgrywanie HDF5 w `/analyze` ładuje **wszystkie** datasety pliku do
  pamięci naraz (`load_hdf5()` z `parsers/hdf5_parser.py` robi to
  eagerly) zanim wybierze, który jest sygnałem — dla pliku z dużą liczbą
  dużych, niepotrzebnych datasetów obok właściwego sygnału może to być
  nieefektywne. Wybór datasetu przy niejednoznacznej nazwie jest
  deterministyczny (alfabetyczny), ale zgadywany — zawsze sprawdź pole
  `hdf5_info`/żółty pasek w dashboardzie, że wybrano właściwy dataset.
- Model J (globalny z-score gradientu) nie jest wiarygodnym detektorem
  zakłóceń na surowych, prawdziwych danych zawierających artefakty
  digitizera — patrz "Realne dane (TCABR)" wyżej.

---

## Licencja

MIT
