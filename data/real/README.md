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

### Uczciwy wynik: Model J na surowym sygnale NIE wykrywa zadnego z 3 realnych zaklocen

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

Po recznym odcieciu pierwszych 80us (samego artefaktu) czulosc odwraca
sie w druga strone: setki wykryc na caly przebieg (zamiast 3) - 2 z 3
strzalow dostaja wtedy trafienie w promieniu 3ms od prawdziwego czasu
zaklocenia, ale gubi sie to wsrod setek innych wykryc, a trzeci strzal
(22201) nie trafia wcale.

**Wniosek**: prosty globalny z-score gradientu (Model J w obecnej
postaci) nie jest wiarygodnym detektorem zaklocen na prawdziwych danych
bez powazniejszego przetworzenia wstepnego (usuniecie artefaktow
digitizera, normalizacja lokalna/w oknie zamiast globalnej na caly
przebieg). To NIE zostalo tu naprawione, zeby wynik nie byl dostrajany po
fakcie (dokladnie to, przed czym przestrzega protokol anty-numerologiczny
reszty ekosystemu TIMDR) - zaraportowane wprost jako ograniczenie.

## Jak dodac wiecej realnych strzalow

`demo/scenarios.py::_load_real_tcabr_scenarios()` wczytuje
`tcabr_samples_metadata.json` automatycznie przy starcie - dopisz kolejny
obiekt do `"samples"` (schema: `shot_id`, `disruptive`, `disruption_time_s`,
`disruption_time_method`, `channels: [{channel, file, n_samples}]`,
`source`) i wrzuc odpowiadajace CSV (`time,signal`) obok - dashboard
podniesie je bez zmian w kodzie.
