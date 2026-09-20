# Prawdziwe dane

Ten katalog zawiera PRAWDZIWE (nie syntetyczne) sygnaly do
`TIMDR-fusion-tools` - w odroznieniu od `data/w7x_mirnov_example.csv`,
ktory jest syntetyczny (patrz `data/example_metadata.json`).

## TCABR (Zenodo, DOI 10.5281/zenodo.21843354)

Zrodlo: "Experimental Plasma Discharge Dataset from the TCABR Tokamak"
(Universidade de Sao Paulo), CC-BY 4.0, 2189 realnych wyladowan (1754
non-disruptive + 435 disruptive). https://zenodo.org/records/21843354

**5 realnych strzalow x 3 kanaly = 15 sygnalow** sa tu wgrane i
zarejestrowane jako scenariusze w dashboardzie (`tcabr_<shot>_<kanal>`,
widoczne w `GET /scenarios` obok syntetycznych):

| shot_id | typ | czas zaklocenia |
|---|---|---|
| 15569 | disruptive (early) | 0.0566 s |
| 20316 | disruptive (typical) | 0.0746 s |
| 22201 | disruptive (late) | 0.1083 s |
| 33664 | normal | - |
| 36973 | normal | - |

Kanaly: `IPlasma` (prad plazmy, kA), `VLoop` (napiecie petli, V),
`BbMirnovN01` (jedna cewka Mirnova). **Kazdy kanal ma WLASNA, osobna os
czasu** (potwierdzone przez uzytkownika i przez `tcabr_tools.py` -
np. w strzale 33664 `BbMirnovN01` ma 100000 probek przy 500kHz, podczas
gdy `IPlasma`/`VLoop` maja 50000 przy 250kHz) - CSV-y respektuja to,
kazdy plik ma swoja wlasna kolumne `time`.

**Pochodzenie plikow**: ekstrakcja zrobiona przez uzytkownika lokalnie
przy uzyciu oficjalnego `tcabr_tools.py` (dolaczonego do datasetu na
Zenodo) na pobranym `tcabr_data.nc` (4.8 GB - za duzy dla tego sandboxa,
`zenodo.org` jest tez zablokowany przez jego network allowlist), zapisane
jako `.npz` (per strzal: `shot_id`, `<kanal>`, `<kanal>_time_us` dla
kazdego z 3 kanalow). Skonwertowane tutaj do CSV (`time,signal`, zgodnie
z `parsers/csv_parser.py`) - jeden plik na (strzal, kanal).

**Czas zaklocenia** (`disruption_time_s` w `tcabr_samples_metadata.json`)
policzony lokalnie z `IPlasma`, kryterium 2 z metodologii klasyfikacji
opisanej na Zenodo: nagly spadek prądu >30% wzgledem szczytu w oknie 5ms.
Kolejnosc wynikow (0.0566s < 0.0746s < 0.1083s) zgadza sie z etykietami
early/typical/late z nazw plikow `tcabr_tools.py` - niezalezne
potwierdzenie, ze metoda dziala.

### Uczciwy wynik: Model J w TRYBIE GLOBALNYM nie wykrywa zadnego z 3 realnych zaklocen

(Nizej, w sekcji "Czy dalo sie to naprawic?", jest OSOBNY, lepszy wynik
dla trybu lokalnego/skalibrowanego - 2/3. Ta sekcja opisuje wylacznie
domyslny, globalny tryb `gradient_zscore()`.)

To jest udokumentowany, **niepoprawiony po fakcie** wynik (patrz
`model_j_validation_note` w `tcabr_samples_metadata.json` i
`tests/test_real_tcabr.py::test_model_j_raw_signal_finds_none_of_the_real_disruptions`):

Surowy sygnal `IPlasma` ma na samym poczatku (probki 0-1) skok
-152.6 -> 152.5 kA - to artefakt digitizera (najpewniej stan
przed-wyzwalaczem/ustalanie wzmacniacza), nie fizyka. Ten artefakt ma
z-score gradientu ~200 i **dominuje jedno globalne odchylenie
standardowe gradientu**, ktorego Model J uzywa do calego przebiegu naraz
- w efekcie na surowych danych (`threshold=2.0`) Model J wykrywa **0 z 3**
prawdziwych, niezaleznie wyznaczonych zaklocen.

Po recznym odcieciu pierwszych 80us (samego artefaktu, bez zadnej innej
zmiany) czulosc odwraca sie w druga strone: setki wykryc na caly przebieg
(zamiast 3) - 2 z 3 strzalow dostaja wtedy trafienie w promieniu 3ms od
prawdziwego czasu zaklocenia, ale gubi sie to wsrod setek innych wykryc, a
trzeci strzal (22201) nie trafia wcale. **Uwaga - to INNA proba niz
skalibrowany tryb lokalny opisany nizej**: to tylko recznie odciety
artefakt na GLOBALNYM z-score, porzucona jako niewiarygodna (stad
"Wniosek" ponizej). Ten wynik (2/3, pudlo na 22201) jest inny niz wynik
skalibrowanego trybu lokalnego (rowniez 2/3, ale pudlo na 20316) -
przypadkowo ta sama liczba "2/3", ale inna metoda i inny konkretny
strzal, ktory zawodzi.

**Wniosek**: prosty globalny z-score gradientu (Model J w obecnej
postaci) nie jest wiarygodnym detektorem zaklocen na prawdziwych danych
bez powazniejszego przetworzenia wstepnego (usuniecie artefaktow
digitizera, normalizacja lokalna/w oknie zamiast globalnej na caly
przebieg).

### Czy dalo sie to naprawic? Tak - skalibrowane, nie dostrojone

Zostawienie artefaktu digitizera bez probowania go usunac bylo bledem -
to nie jest niejednoznaczna decyzja naukowa, tylko rozpoznany blad
instrumentu (jedna probka, stan przed-wyzwalaczem), ktorego wykluczenie
jest standardowym, uzasadnionym czyszczeniem danych. Kluczowe rozroznienie:
**kalibracja** (stala wyliczona z fizycznej wlasciwosci instrumentu,
identyczna dla kazdego sygnalu, NIGDY z polozenia znanego zdarzenia) to co
innego niz **dostrajanie po fakcie** (prog dobrany tak, zeby konkretny
znany wynik wyszedl "dobrze") - to drugie jest dokladnie tym, przed czym
przestrzega protokol anty-numerologiczny reszty ekosystemu TIMDR, to
pierwsze nie.

`gradient_zscore()` w `model_j/model_j_detector.py` ma teraz opcjonalny
parametr `window` - lokalna normalizacja (mediana/MAD gradientu w oknie
przesuwnym) zamiast jednej globalnej wartosci na caly przebieg. Pierwsza
proba (mediana/MAD bez zadnej podlogi) psula sie numerycznie: ten sygnal
jest dosc grubo skwantowany przez digitizer (krok kwantyzacji `IPlasma`
~0.0745 kA, tylko ~1200 unikalnych wartosci na 45-50 tys. probek), wiec w
wielu oknach mediana odchylenia bezwzglednego (MAD) gradientu wychodzi
(prawie) dokladnie zero (plaskie, skwantyzowane odcinki), co przy
dzieleniu dawalo z-score rzedu milionow zamiast sensownej liczby.
Naprawiono to podloga dla MAD wyliczona z `_estimate_quantization_step()`
- polowa zmierzonego kroku kwantyzacji SAMEGO sygnalu (mediana odstepu
miedzy kolejnymi, roznymi wartosciami) - fizyczna wlasciwosc instrumentu,
mierzona identycznie dla kazdego z 5 strzalow (zaklocajacych i
normalnych), bez zadnego odniesienia do czasu zaklocenia.

**Wynik na `IPlasma`, `gradient_zscore(window=1001)`, `threshold=5.0`**
(zweryfikowane w `tests/test_real_tcabr.py`):

| strzal | typ | wykryc razem | w tym w +-10ms od zaklocenia |
|---|---|---|---|
| 15569 | zaklocajacy | 101 | 97 (96%) |
| 22201 | zaklocajacy | 37 | 34 (92%) |
| 20316 | zaklocajacy | 23 | 4 (17%) |
| 33664 | normalny | 247 | - |
| 36973 | normalny | 95 | - |

Dla 2 z 3 strzalow zaklocajacych (15569, 22201) zdecydowana wiekszosc
WSZYSTKICH wykryc lokalnego Modelu J skupia sie w waskim, 20ms oknie
wokol prawdziwego, niezaleznie wyznaczonego czasu zaklocenia - to realny,
uzyteczny sygnal, ktorego globalny z-score nie dawal WCALE (0/3 w kazdym
oknie). Trzeci strzal (20316) NIE pokazuje takiej koncentracji, mimo tej
samej, niedostrojonej metody - uczciwie **2/3, nie 3/3**.

Osobne, wazne zastrzezenie: sama SUROWA LICZBA wykryc nie odroznia
strzalow zaklocajacych od normalnych (normalne strzaly daja porownywalne
lub wieksze liczby - 95-247 vs 23-101) - informatywna jest KONCENTRACJA W
CZASIE, nie sam fakt przekroczenia progu (ten sam wniosek co dla
syntetycznych `quiet`/`single_burst` w README.md).

**Co z tego wynika praktycznie**: lokalna, kalibrowana normalizacja to
realna poprawa wzgledem globalnej (ujawnia sygnal, ktorego globalna wersja
w ogole nie widzi), ale to nadal nie jest niezawodny, gotowy detektor
zaklocen (2/3, wymaga analizy koncentracji w czasie, nie samego progu).
Repozytorium ma juz jednak dzialajacy, zwalidowany detektor do tego
konkretnego zadania - to wlasnie kryterium 2 (spadek pradu >30% w oknie
5ms) uzyte wyzej do policzenia `disruption_time_s`, ktore poprawnie i
niezaleznie odtworzylo kolejnosc early/typical/late na wszystkich 3
strzalach. Dla realnych zaklocen plazmy to ono jest wlasciwym narzedziem
produkcyjnym; lokalny Model J zostaje udokumentowany jako czesciowo
dzialajacy, ogolny detektor - uzyteczny do eksploracji, nie do
ostatecznej diagnozy.

## Jak dodac wiecej realnych strzalow

`demo/scenarios.py::_load_real_tcabr_scenarios()` wczytuje
`tcabr_samples_metadata.json` automatycznie przy starcie - dopisz kolejny
obiekt do `"samples"` (schema: `shot_id`, `disruptive`, `disruption_time_s`,
`disruption_time_method`, `channels: [{channel, file, n_samples}]`,
`source`) i wrzuc odpowiadajace CSV (`time,signal`) obok - dashboard
podniesie je bez zmian w kodzie.
