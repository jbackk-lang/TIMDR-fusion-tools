https://jbackk-lang.github.io/

# fusion-tools

Narzędzia do analizy sygnałów z diagnostyki plazmy (W7-X, JET, DIII-D, EAST)
oparte na TIMDR (redukcja informacji), Λ-τ-ρ (metryki strukturalne
sygnału) oraz Model J (detekcja punktów skrętu).

> **Status repozytorium (sierpień 2026):** ten plik i kod zostały właśnie
> uporządkowane po audycie, który znalazł kilka realnych błędów (patrz
> sekcja "Historia poprawek" na końcu). Wszystko poniżej opisuje kod
> **po** poprawkach.

---

## Cele projektu

- redukcja szumu i nadmiarowości sygnałów z diagnostyk plazmy (TIMDR),
- ekstrakcja prostych cech strukturalnych sygnału (Λ-τ-ρ),
- detekcja punktów skrętu / gwałtownych zmian dynamiki (Model J),
- wczytywanie danych w formatach używanych w fuzji (CSV, HDF5, MDSplus).

To repozytorium **nie zawiera** prawdziwych danych z żadnego urządzenia
fuzyjnego — przykładowy sygnał jest syntetyczny (patrz niżej).

---

## Struktura

```
fusion-tools/
├── data/                       # przykładowy syntetyczny sygnał + metadane
│   ├── w7x_mirnov_example.csv
│   ├── w7x_mirnov_example.h5   # to samo co CSV, jako HDF5 (datasety "time"/"signal")
│   └── example_metadata.json
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
├── model_j/                    # detekcja punktów skrętu
│   └── model_j_detector.py
├── demo/                       # działające demo (skrypt + notebook)
│   ├── run_demo.py
│   └── fusion_demo.ipynb
├── api.py                      # FastAPI backend dla dashboardu
├── static/index.html           # dashboard (Chart.js, jeden plik)
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

Prosty webowy dashboard (jeden plik HTML + Chart.js z CDN, bez build-stepu)
nad tym samym pipeline'em, z wgrywaniem własnego pliku (CSV **lub HDF5**)
albo przykładowego sygnału.

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

1. **Wykres sygnału** — oryginał razem ze zredukowanym TIMDR (na poprawnie
   wyskalowanej osi czasu — patrz punkt 4 w "Historii poprawek") i
   zaznaczonymi punktami skrętu Modelu J.
2. **Dryf Λ-τ-ρ** — drugi wykres (słupkowy), pokazujący Λ, τ, ρ liczone
   **osobno w każdym kolejnym oknie** (`latro_windowed()` w
   `latro_core.py`, ten sam podział na okna co `timdr()`), zamiast jednej
   uśrednionej wartości na cały sygnał. Pozwala zobaczyć, czy i gdzie
   energia/rozrzut sygnału się zmienia w czasie.
3. **Opis wyniku** — krótki, deterministyczny opis po polsku generowany z
   policzonych statystyk (bez wywołania LLM): liczba próbek i redukcja,
   zakres wartości, liczba wykrytych punktów Modelu J pogrupowana w
   odrębne zdarzenia w czasie, oraz kierunek zmiany energii (ρ) między
   początkiem a końcem sygnału. Kończy się zastrzeżeniem, że to opis
   statystyczny, nie interpretacja fizyczna MHD.

Panel ma też przycisk "Anuluj" (ten sam wzorzec co w innych dashboardach w
tej organizacji: `AbortController` po stronie przeglądarki + limit
rozmiaru sygnału po stronie serwera — `MAX_SAMPLES = 200 000` w `api.py` —
żeby duży plik nie zawiesił karty przeglądarki).

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

Przykładowy wynik na wbudowanym sygnale syntetycznym (`window=64`,
`threshold=2.0`, zweryfikowane live przez `POST /analyze`):

```
n_samples: 2000 -> 32 (po TIMDR)
Λ (lambda): 1.9562   τ (tau): 0.3294   ρ (rho): 0.1421
Model J: 74 probki powyzej progu (3.7%), w 11 odrebnych miejscach w czasie

Opis wyniku (generowany automatycznie):
"Sygnal ma 2000 probek, zredukowanych przez TIMDR do 32 (okno=64).
Wartosci miesza sie w zakresie od -0.718 do 1.238 (Lambda = 1.956,
tau = 0.3294, rho = 0.1421). Model J wykryl 74 probek powyzej progu
(3.7% wszystkich probek), skupionych w 11 miejscach w czasie
(kilkanascie odrebnych zdarzen): ~t=0.124..0.21, ~t=0.401..0.565,
~t=0.64..0.653, ~t=0.739..0.761, ~t=0.848 i 6 innych miejscach. Energia
sygnalu (rho) liczona osobno w kolejnych oknach jest wzglednie stabilna
w czasie. Uwaga: to automatyczny, czysto statystyczny opis (bez
interpretacji fizycznej MHD) - patrz sekcja "Zakres i ograniczenia"
w README."
```

(11 klastrów punktów, nie 3 — to oczekiwane: próg `threshold=2.0` łapie
też mniejsze, naturalne wahania gradientu z szumu w sygnale, nie tylko 3
celowo wstrzyknięte zdarzenia. Podniesienie progu w dashboardzie to
ograniczy.)

Endpointy API:

| Endpoint | Metoda | Opis |
|---|---|---|
| `/` | GET | dashboard |
| `/example` | GET | metadane wbudowanego przykładowego sygnału |
| `/analyze` | POST | uruchamia pipeline; pola formularza: `file` (CSV lub HDF5, opcjonalny), `use_example` (bool), `window`, `threshold`, `drop_last`, `dataset` (nazwa datasetu HDF5, opcjonalna) |
| `/data/...` | GET | statyczny dostęp do plików w `data/` (np. pobranie przykładowego `.h5`) |

Odpowiedź `/analyze` zawiera dodatkowo: `latro_windowed` (`{x, lambda,
tau, rho}` per okno), `description` (opis tekstowy) oraz — tylko dla
wgranego HDF5 — `hdf5_info` (`available_datasets`, `signal_dataset`,
`time_dataset`, `time_source`, `ambiguous`).

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
Domyślnie **zachowuje** ostatnie, niepełne okno jako krótszy ostatni
element wyniku (patrz "Historia poprawek" — wcześniej był on cicho
odrzucany). `drop_last=True` przywraca stare zachowanie.

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
(`{"lambda": ..., "tau": ..., "rho": ...}`) — jest cienkim wrapperem nad
`latro()`, żeby nie było dwóch osobnych implementacji do rozjechania się
(patrz "Historia poprawek").

`latro_windowed(signal, window=64, drop_last=False)` — liczy `latro()`
osobno dla każdego kolejnego okna sygnału (ten sam podział na okna co
`timdr()`), zamiast jednej uśrednionej trójki na cały sygnał. Zwraca
`(lambdas, taus, rhos)` — trzy tablice, po jednej wartości na okno. Do
tego, żeby zobaczyć jak Λ-τ-ρ **zmieniają się w czasie**, nie tylko ich
średnią (używane przez dashboard do wykresu "dryfu").

### `model_j/`

`model_j(signal, threshold=2.0)` — liczy gradient sygnału, standaryzuje go
(z-score) i zwraca indeksy próbek, gdzie `|z| > threshold`. To detektor
lokalnych, gwałtownych zmian gradientu ("punktów skrętu"), a nie detektor
lokalnych maksimów.

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
from model_j.model_j_detector import model_j

time, signal = load_csv("data/w7x_mirnov_example.csv")

reduced = timdr(signal, window=64)
lam, tau, rho = latro(signal)
points = model_j(signal, threshold=2.0)

print("Λ-τ-ρ:", lam, tau, rho)
print("Punkty Modelu J:", list(points)[:10])
```

---

## Testy

```bash
pytest tests/ -v
```

Testy obejmują: poprawność `latro()`/`latro_features()`/`latro_windowed()`
(w tym regresję na wcześniejszą niespójność definicji), zabezpieczenie
`model_j()` przed dzieleniem przez zero, zachowanie ostatniego niepełnego
okna w `timdr()`, wczytywanie CSV pod poprawną ścieżką importu, pełny
pipeline end-to-end na przykładowym sygnale (sprawdza, że Model J
faktycznie wykrywa 3 wstrzyknięte zdarzenia), oraz endpointy API
(`tests/test_api.py` — `/analyze` na przykładzie, na wgranym CSV i na
wgranym HDF5 z kilkoma wariantami wyboru datasetu, limit rozmiaru,
odrzucanie nieobsługiwanych rozszerzeń, obecność `latro_windowed` i
`description` w odpowiedzi). 34/34 testów przechodzi.

---

## Zakres i ograniczenia

- Brak prawdziwych danych open-data z W7-X/JET/DIII-D/EAST w repozytorium
  — tylko syntetyczny przykład do demo/testów.
- `parsers/mdsplus_parser.py` nie był uruchamiany przeciw prawdziwemu
  serwerowi MDSplus w tym środowisku — API wygląda poprawnie, ale jest
  nieprzetestowane empirycznie.
- Λ-τ-ρ i Model J to proste metryki/detektory statystyczne w dziedzinie
  czasu, nie zwalidowany model fizyczny MHD. Interpretacje w rodzaju
  "punkty skrętu = wczesne wykrywanie ELM/sawtooth" są hipotezami do
  zweryfikowania na prawdziwych danych, nie potwierdzonym wynikiem.
  "Opis wyniku" w dashboardzie to czysto statystyczne podsumowanie
  (liczby, zakresy, trend) — nie diagnoza plazmy.
- Wgrywanie HDF5 w `/analyze` ładuje **wszystkie** datasety pliku do
  pamięci naraz (`load_hdf5()` z `parsers/hdf5_parser.py` robi to
  eagerly) zanim wybierze, który jest sygnałem — dla pliku z dużą liczbą
  dużych, niepotrzebnych datasetów obok właściwego sygnału może to być
  nieefektywne. Wybór datasetu przy niejednoznacznej nazwie jest
  deterministyczny (alfabetyczny), ale zgadywany — zawsze sprawdź pole
  `hdf5_info`/żółty pasek w dashboardzie, że wybrano właściwy dataset.

---

## Historia poprawek (sierpień 2026)

Audyt tego repozytorium znalazł i naprawił:

1. **Trzy wzajemnie niespójne definicje Λ-τ-ρ** — inna w `latro_core.py`
   (oparta na gradiencie), inna w `latro_features.py` (`tau=std(signal)`),
   jeszcze inna w kodzie demo w README. Skonsolidowane do jednej definicji
   (patrz sekcja `latro/` wyżej); `latro_features()` teraz deleguje do
   `latro()`.
2. **Dzielenie przez zero w `model_j()`** — dla sygnału stałego
   `std(gradient) == 0` dokładnie, co dawało `RuntimeWarning: invalid
   value encountered in divide` i cichy pusty wynik. Dodatkowo dla
   sygnału idealnie liniowego `std(gradient)` wychodzi rzędu `1e-16`
   (szum zmiennoprzecinkowy, nie dokładne zero) — dzielenie przez tak
   małą liczbę wzmacniało ten szum do pozornie dużych z-score i dawało
   fałszywe detekcje na sygnale, który w rzeczywistości jest płaski.
   Zabezpieczenie użyte jest teraz progiem względnym do skali gradientu
   (łapie oba przypadki), zweryfikowane testami regresyjnymi.
3. **`timdr()` cicho gubił ostatnie, niepełne okno** sygnału. Teraz
   domyślnie je zachowuje (`drop_last=True` przywraca stare zachowanie).
4. **`plot_timdr()` rysował zredukowany sygnał na złej osi X** (bez
   korekty pod downsampling), co dawało mylący wykres. Naprawione.
5. **Błędna ścieżka importu w README** — dokumentacja mówiła
   `from parsers.csv_parser import load_csv`, ale plik faktycznie był w
   `tools/parsers/csv_parser.py` (potwierdzone przez `ModuleNotFoundError`
   na żywo). Plik przeniesiony do `parsers/csv_parser.py`, zgodnie z
   dokumentacją i strukturą pozostałych parserów.
6. **README był wewnętrznie zepsuty**: sekcja "Offline Demo" powielona 4
   razy z niespójnym kodem, niedomknięte bloki kodu psujące renderowanie
   na GitHubie, oraz przypadkowo wklejona cała treść README organizacji
   jbackk-lang wewnątrz README tego repo. Przepisane od zera.
7. Brak `requirements.txt`, brak działającego notebooka demo (`
   fusion_demo.ipynb` był pustym/niepoprawnym JSON-em), brak przykładowego
   pliku sygnału mimo odwołań do niego w README, zero testów — wszystko
   dodane.

Kolejna runda dodała webowy dashboard (`api.py` + `static/index.html` +
`run.bat`), a potem — na wyraźną prośbę — trzy rozszerzenia:

8. **Wgrywanie HDF5** w `/analyze`, obok CSV — z jawną (nie cichą) logiką
   wyboru datasetu czasu/sygnału i przykładowym plikiem
   `data/w7x_mirnov_example.h5` do testów.
9. **`latro_windowed()`** — Λ-τ-ρ liczone osobno w każdym oknie zamiast
   jednej sumarycznej wartości na cały sygnał, pokazane jako drugi wykres
   (dryf w czasie) w dashboardzie.
10. **Automatyczny opis wyniku** — deterministyczny tekst po polsku
    generowany z policzonych statystyk (bez LLM), z jawnym zastrzeżeniem,
    że to opis statystyczny, nie interpretacja fizyczna.

Zgłoszenie: po `run.bat` przeglądarka "migała i gasła", odświeżanie nic
nie dawało, "jakby serwer się wyłączał". Diagnoza (`.venv` od
wcześniejszego uruchomienia było już w repo, więc dało się sprawdzić
naprawdę zainstalowane wersje zamiast zgadywać — Python 3.11.0, fastapi
0.141.1, wszystkie zależności obecne i zgodne z tym, co jest testowane w
CI) wykluczyła "brakującą zależność" jako przyczynę, ale przy okazji
znalazła dwa realne, niezależne błędy:

11. **`file: UploadFile | None` i `dataset: str | None` w `/analyze`** —
    składnia `X | None` w adnotacji typu działa tylko na Pythonie 3.10+;
    na starszym Pythonie `api.py` wywaliłby się `TypeError` **przy
    starcie**, zanim serwer w ogóle by wstał. Zmienione na
    `Optional[X]` (`typing`), które działa od Pythona 3.8 — niezależnie
    od tego, czy to była faktyczna przyczyna zgłoszenia, to realne
    zawężenie wymagań (repo wymagało 3.10+ bez potrzeby).
12. **`run.bat` nie miał `pause` po linii z uvicornem** — jeśli serwer
    wywalał się od razu po starcie, okno konsoli (odpalone dwuklikiem)
    znikało natychmiast, zanim dało się przeczytać traceback — dokładnie
    objaw "miga i gaśnie". Dodany bezwarunkowy `pause` na końcu.
13. **Brak sprawdzenia zajętego portu 8000** — jeśli poprzednie
    uruchomienie nie zamknęło się czysto (np. zamknięcie okna "krzyżykiem"
    zamiast Ctrl+C), `python.exe` czasem zostaje jako proces w tle nadal
    trzymający port. Kolejne uruchomienie wtedy natychmiast wywala się
    błędem "address already in use" — przeglądarka pokazuje martwą
    stronę, dokładnie jak "serwer się wyłączył", mimo że nowy serwer nigdy
    nie wstał. `run.bat` teraz sprawdza to z wyprzedzeniem
    (`netstat`/`findstr`) i podpowiada jak zabić zawieszony proces zamiast
    ciszy.
14. **`from parsers.hdf5_parser import load_hdf5` (a wewnątrz `import
    h5py`) był twardym importem na górze `api.py`** — gdyby instalacja
    `h5py` na czyimś Windowsie zawiodła (h5py ma binarne rozszerzenie),
    cały dashboard, łącznie z obsługą CSV niezwiązaną z h5py, w ogóle by
    nie wystartował. Import jest teraz w `try/except`; brak/zepsute h5py
    wyłącza tylko obsługę HDF5 z czytelnym komunikatem 400, reszta działa
    normalnie. Zweryfikowane symulując brak h5py w teście.

Punkty 11-14 zostały naprawione i zweryfikowane (34/34 testów + symulacja
brakującego h5py), ale nie udało się jednoznacznie potwierdzić, który z
nich (jeśli którykolwiek) był rzeczywistą przyczyną zgłoszonego problemu —
bez dokładnego komunikatu błędu z ekranu użytkownika to najbardziej
prawdopodobne kandydaci, nie potwierdzona diagnoza.

---

## Licencja

MIT
