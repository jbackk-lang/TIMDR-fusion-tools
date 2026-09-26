# Audyt twierdzeń: README → sekcja MAST (TIMDR-fusion-tools)

Wygenerowano: 2026-09-26 11:36 UTC; reguły: `data/mast_cross_device/CLAIM_AUDIT_PREREG.md` (sha256 1e544865d0f7), karty: `claims_mast.py` (sha256 272f5705f902), README sha256 da2d0b44d605.

Werdykty kart: NIEROZSTRZYGNIĘTE 1, POTWIERDZONE 10, SPRZECZNE 2, UDOKUMENTOWANE 3.

## Twierdzenia

| # | Twierdzenie (cytat z README) | Werdykt | Przeliczenie | Uwagi |
| --- | --- | --- | --- | --- |
| M1 | uruchomione bez zmian kodu | POTWIERDZONE | sha256 908ee2f2855c | zgodny z hashem zamrożonym w obu pre-rejestracjach |
| M2 | na dwóch rozłącznych próbkach po 579 strzałów MAST | POTWIERDZONE | listy 579/579, wyniki 579/579, wspólne 0 |  |
| M3 | (`magnetics/ip` | SPRZECZNE | brak w skrypcie |  |
| M4 | parametry okienkowe przeliczone na czas fizyczny | POTWIERDZONE | dt=0,2 ms → smooth_window=1, exclude_start=40, long_window=25, short_window=21 | reguła TCABR 4 µs → MAST z PREREGISTRATION.md, zgodna z oboma skryptami |
| M5 | kryteria zamrożone przed uruchomieniem | NIEROZSTRZYGNIĘTE | 8 hashy zgodnych | R6: pre-rejestracja i wyniki w tym samym commicie (PREREGISTRATION.md: commit 38937f0 = wyniki 38937f0; PREREGISTRATION_2.md: commit adc21c8 = wyniki adc21c8); moment zamrożenia tylko deklarowany znacznikiem frozen_at_utc |
| M6 | rozkład czasu zaniku jest dwumodalny | POTWIERDZONE | próbka 1: ΔBIC 403, wagi 0,62/0,38, stosunek 23; próbka 2: ΔBIC 481, wagi 0,42/0,58, stosunek 5 | EM w NumPy, kryteria K4 |
| M7 | (ok. 2–3 ms i ok. 50 ms | SPRZECZNE | próbka 1: 2,24 i 52,2 ms; próbka 2: 2,76 i 14,6 ms | tolerancja ±15% |
| M8 | przerwa 4–15 ms zawiera ok. 4,5% strzałów | POTWIERDZONE | próbka 1: 4,5%, próbka 2: 4,5% | tolerancja ±1,0 pp |
| M9 | i powtarzalny w obu próbkach | POTWIERDZONE | K4 i przerwa ≤ 10% w obu próbkach | próbka 1 była eksploracyjna (kryteria z niej wyprowadzone), potwierdzenie daje tylko próbka 2 |
| M10 | próg 15 ms z TCABR działa tak samo jak 7,7 ms | POTWIERDZONE | różnica odsetka szybkich 15 vs 7,7 ms: 2,4% i 2,4% (tolerancja K5 ≤ 5 pp) | zgodność w tolerancji, nie równość - patrz R7b |
| M11 | To opis struktury rozkładu, nie trafność klasyfikacji | UDOKUMENTOWANE | zapis w PREREGISTRATION.md | zakres zadeklarowany z góry |
| M12 | dla MAST nie ma dostępnych etykiet dysrupcji (`level2/defuse`: AccessDenied) | UDOKUMENTOWANE | zapis w obu pre-rejestracjach | stanu dostępu do level2/defuse nie da się sprawdzić z plików (wymaga sieci) |
| M13 | szybki tryb (ok. 65% strzałów) | POTWIERDZONE | próbka 1: 64,6%, próbka 2: 65,6% | tolerancja ±2,0 pp |
| M14 | `bridge_detector()` nie wykazał na MAST związku z `is_fast_quench()` | POTWIERDZONE | próbka 1: 73,8% vs 71,7% (różnica +2.1 pp), p = 0,62; próbka 2: 76,6% vs 74,9% (różnica +1.7 pp), p = 0,68 | dokładny test Fishera; odsetek strzałów z wykryciem mostu wśród szybkich vs wolnych |
| M15 | pokazuje powtarzalną dwumodalność czasu zaniku, nie skuteczność klasyfikacji na MAST | POTWIERDZONE | K4 i przerwa ≤ 10% w obu próbkach | próbka 1 była eksploracyjna (kryteria z niej wyprowadzone), potwierdzenie daje tylko próbka 2 |
| M16 | `phasespace_funnel_ratio()` nie był na MAST testowany (Vloop z rekonstrukcji EFIT ma zbyt rzadkie próbkowanie, 5 ms, z lukami) | UDOKUMENTOWANE | PREREGISTRATION.md: 155 pkt co 5 ms, część NaN | żaden skrypt MAST nie wywołuje phasespace_funnel_ratio |

## Reguły całego fragmentu

| Reguła | Wynik | Szczegóły |
| --- | --- | --- |
| R4 świeżość | POTWIERDZONE | 8 plikow zgodnych z zamrozonymi hashami |
| R5 kompletność | BRAK KOMPLETNOŚCI | data/mast_cross_device/summary.txt: pre-rejestrowane kryterium K1 w próbce 1 niespełnione; README tego nie podaje |
| R5 kompletność | BRAK KOMPLETNOŚCI | data/mast_cross_device/PREREGISTRATION_2.md: kryteria K1', K4, K5 wyprowadzone z próbki 1 (post hoc); README tego nie podaje |
| R6 kotwica | NIEROZSTRZYGNIĘTE | data/mast_cross_device/PREREGISTRATION.md i data/mast_cross_device/results.csv w tym samym lub pozniejszym commicie (38937f0 / 38937f0) - zamrozenie tylko deklarowane |
| R6 kotwica | NIEROZSTRZYGNIĘTE | data/mast_cross_device/PREREGISTRATION_2.md i data/mast_cross_device/results2.csv w tym samym lub pozniejszym commicie (adc21c8 / adc21c8) - zamrozenie tylko deklarowane |
| R7b sformułowanie | DO ZŁAGODZENIA | „tak samo”: dowód to zgodność w tolerancji, nie równość - podaj różnicę |

## Analiza rozbieżności (po uruchomieniu, post hoc — karty i reguły NIE zostały zmienione)

**M3 — błąd karty, ale ujawnia lukę w odtwarzalności.** Karta szukała `magnetics/ip` w obu skryptach uruchomieniowych.
`run_mast_frozen2.py` czyta `magnetics/ip` bezpośrednio z surowych chunków. `run_mast_frozen.py` (próbka 1) czyta gotowy plik
`/tmp/w/data.pkl` — sygnał pochodzi z `magnetics/ip` (tak mówią `fetch_mast_batch.py` i PREREGISTRATION.md), ale **krok
dekodowania chunków do `data.pkl` nie jest w repozytorium**. Twierdzenie README nie jest fałszywe; fałszywa była karta
(za wąska). Właściwy werdykt: NIEROZSTRZYGNIĘTE dla próbki 1 do czasu dołączenia kroku dekodowania albo ponownego przeliczenia
próbki 1 loaderem z `run_mast_frozen2.py` i porównania z `results.csv`.

**M7 — opis składowych zależy od lokalnego optimum dopasowania.** W próbce 1 oba starty EM dają to samo (2,24 i 52,2 ms,
log-likelihood −425,1). W próbce 2 start z podziału przy 8 ms (odpowiednik inicjalizacji k-means w sklearn) daje 2,31 i 52,9 ms
(ll −410,6, zgodnie z `summary2.txt`), ale lepsze dopasowanie (ll −376,9) to wąski pik 2,76 ms (sd 0,063 w log10) plus szerokie
tło wokół 14,6 ms (sd 0,81), wagi 0,42/0,58. Wartości 2,32 i 53,31 ms w teście potwierdzającym pochodzą więc z lokalnego optimum
sklearn. K4 nadal jest spełnione przy lepszym dopasowaniu (ΔBIC 481, wagi ≥ 0,20, stosunek 5,3 ≥ 5 — blisko progu), więc
werdykt testu potwierdzającego się nie zmienia; zmienia się tylko to, że „ok. 50 ms” nie jest jednoznaczną cechą rozkładu.
Opis niezależny od modelu jest stabilny w obu próbkach: mediana czasu zaniku poniżej 4 ms = 2,6 ms; powyżej 15 ms = 60,8 ms
(próbka 1) i 62,0 ms (próbka 2), IQR ok. 30–98 ms.

**R5 — brak kompletności (rzeczywista luka w README).** README opisuje wynik potwierdzający, ale nie podaje, że pre-rejestrowane
kryterium K1 w próbce 1 nie zostało spełnione (11,1% > 10%) i że kryteria K1', K4, K5 wyprowadzono post hoc z próbki 1.
Obie informacje są w `summary.txt`, `EXPLORATORY_NOTES.md` i PREREGISTRATION_2.md, ale czytelnik README ich nie zobaczy.

**R6 — zamrożenie tylko deklarowane.** Pre-rejestracje i wyniki trafiły do gita w tych samych commitach (38937f0, adc21c8).
Integralność hashy jest zgodna (R4), ale kolejność „kryteria przed wynikami” opiera się wyłącznie na znaczniku `frozen_at_utc`.
Dla kolejnych testów: commit pre-rejestracji przed pobraniem danych (tak zrobiono w tym audycie: commit 8a23c55).

**R7b — „tak samo”.** Odsetek szybkich strzałów przy progu 15 ms i 7,7 ms różni się o 2,4 pp w obu próbkach — zgodność w
pre-rejestrowanej tolerancji (≤ 5 pp), nie równość.

## Proponowane zmiany README (do decyzji autora)

- „(ok. 2–3 ms i ok. 50 ms, …)” → „(mediany ok. 2,6 ms i ok. 61 ms, …)”, z dopiskiem, że parametry mieszaniny Gaussa zależą od
  inicjalizacji.
- „próg 15 ms z TCABR działa tak samo jak 7,7 ms” → „próg 15 ms z TCABR daje prawie ten sam podział co 7,7 ms (różnica 2,4 pp)”.
- Dopisać: „Pierwsza pre-rejestracja (próbka 1) nie przeszła kryterium K1 (11,1% > 10%, okno 7,5–30 ms źle obejmowało dolną część
  trybu wolnego); kryteria testu potwierdzającego wyprowadzono z próbki 1 i sprawdzono na rozłącznej próbce 2.”
- Dołączyć skrypt dekodowania próbki 1 albo przeliczyć próbkę 1 loaderem z `run_mast_frozen2.py`.
