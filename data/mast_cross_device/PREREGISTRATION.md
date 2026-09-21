# MAST cross-device: pre-rejestracja testu quench_duration / is_fast_quench / bridge_detector

Status: SZKIC, zamrozony przed uruchomieniem jakiegokolwiek detektora na danych MAST.
Jedyny obejrzany dotad sygnal MAST: strzal 30421 (kształt, jednostki, próbkowanie; detektory NIE były na nim uruchamiane).

## Dane
- Źródło: s3.echo.stfc.ac.uk / mast/level2/shots (11 573 strzałów, 11766-30471), sygnał `magnetics/ip` + `magnetics/time` (krok ~0,2 ms).
- Próbka: co 20. strzał z numerycznie posortowanej listy (indeksy 0,20,40,...), lista i jej sha256 zapisywane przez fetch_mast_batch.py (shot_list_frozen.txt).
- Brak etykiet dysrupcji (level2/defuse zablokowane: AccessDenied). Test NIE mierzy trafności klasyfikacji, tylko strukturę rozkładu.

## Reguła przenoszenia parametrów (TCABR -> MAST)
TCABR: dt = 4 us. MAST: dt = mediana różnic magnetics/time (~200 us). Parametry okienkowe (w próbkach) przeliczane na czas fizyczny:
n_MAST = round(n_TCABR * 4us / dt_MAST), min 1; jeśli oryginał nieparzysty -> najbliższa nieparzysta.
- quench_duration: fraction_high=0.70, fraction_low=0.10 (bez zmian); smooth_window 51 -> 1; exclude_start 2000 -> 40 (8 ms); dt=dt_MAST [s].
- is_fast_quench: duration_threshold = 0.015 s (bez zmian, wartość fizyczna).
- bridge_detector: drop_fraction=0.30, short_threshold=5.0 (bez zmian, bezwymiarowe); long_window 1250 -> 25; short_window 1001 -> 21; exclude_start 2000 -> 40.
Żaden parametr nie jest dostrajany po zobaczeniu wyników MAST.

## Kryteria (zamrożone)
K1 (bimodalność, quench_duration): wśród strzałów z niepustym wynikiem, odsetek z d w [7,5; 30] ms (czynnik 2 wokół progu 15 ms) <= 10%. TCABR miał ~6-krotny margines.
K2 (pokrycie): odsetek strzałów z quench_duration != None >= 80%; odsetek pominiętych/zepsutych strzałów raportowany osobno.
K3 (spójność wewnętrzna, bridge_detector): raportujemy rozkład liczby wykryć na strzał oraz zgodność z is_fast_quench (tabela 2x2). To NIE jest trafność.
Wynik: K1 spełnione / niespełnione, raportowane wprost, także gdy niekorzystne. Niepowodzenie nie prowadzi do zmiany progów w tym teście.

## Znane ograniczenia (zapisane z góry)
- Bez etykiet: "szybki quench" != "dysrupcja"; MAST może mieć szybkie, ale planowe wygaszenia i wolne dysrupcje.
- Inne urządzenie (tokamak sferyczny, Ip ~0,65 MA vs TCABR): skala czasowa quenchu może być inna, co jest częścią testowanej hipotezy transferu.
- phasespace_funnel_ratio nie jest testowany (Vloop z EFIT: 155 pkt co 5 ms, część NaN).
- Ewentualne późniejsze etykiety (defuse / mastapp.site) -> drugi test na tych samych zamrożonych parametrach.
