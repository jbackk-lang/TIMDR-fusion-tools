# Audyt twierdzeń: README → sekcja MAST (TIMDR-fusion-tools)

Silnik: claim_audit v0.2 (TIMDR-AI-Core).

Drugi przebieg, po poprawkach README i odtworzeniu próbki 1 (zmiany: `CLAIM_AUDIT_ADDENDUM_1.md`). Pierwszy przebieg z analizą rozbieżności: `CLAIM_AUDIT_v1.md`. Karty zmieniono po pierwszym przebiegu, więc ten raport sprawdza zgodność poprawionego README z plikami, a nie jest niezależnym testem.

Wygenerowano: 2026-09-26 11:45 UTC; reguły: `data/mast_cross_device/CLAIM_AUDIT_PREREG.md` (sha256 1e544865d0f7), karty: `claims_mast.py` (sha256 30a2e6f8cadb), README sha256 928ac9a1ec5c.

Werdykty kart: POTWIERDZONE 15, UDOKUMENTOWANE 3.

## Twierdzenia

| # | Twierdzenie (cytat z README) | Werdykt | Przeliczenie | Uwagi |
| --- | --- | --- | --- | --- |
| M1 | uruchomione bez zmian kodu | POTWIERDZONE | sha256 908ee2f2855c | zgodny z hashem zamrożonym w obu pre-rejestracjach |
| M2 | na dwóch rozłącznych próbkach po 579 strzałów MAST | POTWIERDZONE | listy 579/579, wyniki 579/579, wspólne 0 |  |
| M3 | (`magnetics/ip` | POTWIERDZONE | pobieranie magnetics/ip w obu próbkach; loader próbki 2 czyta magnetics/ip; próbka 1 odtworzona tym loaderem: 0 różnic |  |
| M4 | parametry okienkowe przeliczone na czas fizyczny | POTWIERDZONE | dt=0,2 ms → smooth_window=1, exclude_start=40, long_window=25, short_window=21 | reguła TCABR 4 µs → MAST z PREREGISTRATION.md, zgodna z oboma skryptami |
| M5 | Kryteria zamrożono hashami przed uruchomieniem, ale pre-rejestracje trafiły do gita razem z wynikami, więc kolejność potwierdza tylko zapisany znacznik czasu | POTWIERDZONE | 8 hashy zgodnych; wspólne commity: 38937f0, adc21c8 | oba zdania twierdzenia zgodne z plikami i historią gita |
| M6 | Rozkład czasu zaniku jest dwumodalny | POTWIERDZONE | próbka 1: ΔBIC 403, wagi 0,62/0,38, stosunek 23; próbka 2: ΔBIC 481, wagi 0,42/0,58, stosunek 5 | EM w NumPy, kryteria K4 |
| M7 | (mediany skupień ok. 2,6 ms i ok. 61 ms; parametry mieszaniny Gaussa zależą od inicjalizacji dopasowania) | POTWIERDZONE | próbka 1: 2,6 i 60,8 ms; próbka 2: 2,6 i 62,0 ms | mediany d < 4 ms i d > 15 ms (±15%); składowe GMM różnią się zależnie od startu EM w próbkach: [2] |
| M8 | przerwa 4–15 ms zawiera ok. 4,5% strzałów w obu próbkach | POTWIERDZONE | próbka 1: 4,5%, próbka 2: 4,5% | tolerancja ±1,0 pp |
| M10 | próg 15 ms z TCABR daje prawie ten sam podział co 7,7 ms (różnica 2,4 pp) | POTWIERDZONE | różnica: 2,4 i 2,4 pp | „prawie ten sam” = w tolerancji K5 (≤ 5 pp) |
| M11 | To opis struktury rozkładu, nie trafność klasyfikacji | UDOKUMENTOWANE | zapis w PREREGISTRATION.md | zakres zadeklarowany z góry |
| M12 | dla MAST nie ma dostępnych etykiet dysrupcji (`level2/defuse`: AccessDenied) | UDOKUMENTOWANE | zapis w obu pre-rejestracjach | stanu dostępu do level2/defuse nie da się sprawdzić z plików (wymaga sieci) |
| M13 | szybki tryb (ok. 65% strzałów) | POTWIERDZONE | próbka 1: 64,6%, próbka 2: 65,6% | tolerancja ±2,0 pp |
| M14 | `bridge_detector()` nie wykazał na MAST związku z `is_fast_quench()` | POTWIERDZONE | próbka 1: 73,8% vs 71,7% (różnica +2.1 pp), p = 0,62; próbka 2: 76,6% vs 74,9% (różnica +1.7 pp), p = 0,68 | dokładny test Fishera; odsetek strzałów z wykryciem mostu wśród szybkich vs wolnych |
| M15 | pokazuje powtarzalną dwumodalność czasu zaniku, nie skuteczność klasyfikacji na MAST | POTWIERDZONE | K4 i przerwa ≤ 10% w obu próbkach | próbka 1 była eksploracyjna (kryteria z niej wyprowadzone), potwierdzenie daje tylko próbka 2 |
| M16 | `phasespace_funnel_ratio()` nie był na MAST testowany (Vloop z rekonstrukcji EFIT ma zbyt rzadkie próbkowanie, 5 ms, z lukami) | UDOKUMENTOWANE | PREREGISTRATION.md: 155 pkt co 5 ms, część NaN | żaden skrypt MAST nie wywołuje phasespace_funnel_ratio |
| M17 | Pierwsza pre-rejestracja (próbka 1) **nie przeszła** kryterium K1 (11,1% strzałów w oknie 7,5–30 ms przy progu 10%) | POTWIERDZONE | próbka 1: 11,1% w [7,5; 30] ms, próg z PREREGISTRATION.md 10% |  |
| M18 | Kryteria testu potwierdzającego wyprowadzono post hoc z próbki 1 i sprawdzono na rozłącznej próbce 2 — tam wszystkie są spełnione | POTWIERDZONE | próbka 2: K1' 4,5%, K2 100,0%, K4 tak, K5 2,4% | PREREGISTRATION_2.md: kryteria wyprowadzone z próbki 1 |
| M19 | odtworzenie próbki 1 z surowych danych | POTWIERDZONE | results1_repro.csv vs results.csv: 0 różnic | REPRODUCTION_SAMPLE1.md |

## Reguły całego fragmentu

| Reguła | Wynik | Szczegóły |
| --- | --- | --- |
| R4 świeżość | POTWIERDZONE | 8 plikow zgodnych z zamrozonymi hashami |
| R5 kompletność | POTWIERDZONE | pre-rejestrowane kryterium K1 w próbce 1 niespełnione - README to podaje |
| R5 kompletność | POTWIERDZONE | kryteria K1', K4, K5 wyprowadzone z próbki 1 (post hoc) - README to podaje |
| R6 kotwica | UJAWNIONE | data/mast_cross_device/PREREGISTRATION.md i data/mast_cross_device/results.csv w tym samym commicie (38937f0 / 38937f0); README opisuje to ograniczenie |
| R6 kotwica | UJAWNIONE | data/mast_cross_device/PREREGISTRATION_2.md i data/mast_cross_device/results2.csv w tym samym commicie (adc21c8 / adc21c8); README opisuje to ograniczenie |
