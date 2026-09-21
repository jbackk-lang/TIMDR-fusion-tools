# MAST cross-device, test potwierdzajacy (probka 2) - pre-rejestracja

Status: ZAMROZONE przed pobraniem probki 2 (zadne dane probki 2 nie zostaly obejrzane).
Powiazane: PREREGISTRATION.md, ADDENDUM_1.md, EXPLORATORY_NOTES.md (probka 1).

## Po co ten test
W probce 1 kryterium K1 (okno 7,5-30 ms) zostalo spelnione zle, bo wpadlo w dolna czesc trybu wolnego. Analiza post hoc probki 1 wskazala,
ze rozklad czasu zaniku jest dwumodalny z przerwa ok. 4-15 ms. Kryteria K1', K4, K5 ponizej zostaly WYPROWADZONE z probki 1,
wiec probka 1 nie moze ich potwierdzic. Ten test sprawdza je na niezaleznej probce 2.

## Dane
- Zrodlo jak wczesniej: mast/level2/shots, magnetics/ip + magnetics/time.
- Probka 2: co 20. strzal z numerycznie posortowanej listy, przesuniety o 10 (indeksy 10, 30, 50, ...), rozlaczna z probka 1 (skrypt sprawdza asercja).
- Bez etykiet dysrupcji (level2/defuse: AccessDenied). Test opisuje strukture rozkladu, NIE trafnosc klasyfikacji.

## Detektory i parametry
Bez zmian wzgledem PREREGISTRATION.md: quench_duration(fraction_high=0,70, fraction_low=0,10, smooth_window=1, exclude_start=40), is_fast_quench(duration_threshold=0,015 s),
bridge_detector(long_window=25, drop_fraction=0,30, short_window=21, short_threshold=5,0, exclude_start=40). Kod: model_j_detector.py, sha256 908ee2f2...1734 (bez modyfikacji).
Prog is_fast_quench pozostaje 15 ms, MIMO ze dane probki 1 sugeruja granice ok. 7,7 ms - nie zmieniamy go po fakcie; K5 sprawdza, czy to ma znaczenie.

## QC (zamrozone)
Regula R1: jesli |min(x[40:])| > |max(x[40:])|, ip := -ip. Strzal niepoprawny (blad dekodowania, dlugosc <= 200, NaN, dt nierownomierny > 1%) jest raportowany i liczy sie jako niepokryty
w K2. Zadnych innych wykluczen.

## Kryteria (wszystkie liczone na strzalach z niepustym quench_duration, o ile nie zaznaczono inaczej)
- K1' (przerwa): odsetek strzalow z czasem zaniku d w [4 ms, 15 ms] <= 10%. (Probka 1: 4,5%.)
- K2 (pokrycie): odsetek strzalow probki z niepustym quench_duration >= 80%, mianownik = wszystkie strzaly probki.
- K4 (dwumodalnosc): mieszanina 2 skladnikow w log10(d [ms]) (sklearn GaussianMixture, n_init=10, random_state=0): BIC(k=1) - BIC(k=2) > 10,
  obie wagi >= 0,20, stosunek srednich skladnikow >= 5. (Probka 1: dBIC 403, skladniki 2,2 i 52 ms, wagi 0,62/0,38.)
- K5 (odpornosc na prog): |odsetek(d < 15 ms) - odsetek(d < 7,7 ms)| <= 5 punktow procentowych. (Probka 1: 2,4 pp.)
Werdykt CALEGO testu: "potwierdzone" tylko gdy K1', K2, K4, K5 wszystkie spelnione. Wynik czastkowy raportowany wprost. Niepowodzenie nie prowadzi do zmiany progow w tym tescie.

## Opisowo (bez progow)
Odsetek szybkich, granica 50/50 miedzy skladnikami, kwantyle i histogram d, odsetek szybkich wg kampanii, zgodnosc bridge_detector z is_fast_quench.

## Znane ograniczenia (z gory)
- Brak etykiet: "szybki zanik" != "dysrupcja". Potwierdzenie dwumodalnosci nie dowodzi, ze szybki tryb to dysrupcje.
- Granice przedzialow (4 i 15 ms) leza na siatce 0,2 ms; wartosci rowne dokladnie granicy moga zalezec od zaokraglen zmiennoprzecinkowych (raportowane jak wychodzi z kodu).
- Probka 2 pochodzi z tej samej populacji strzalow MAST co probka 1 (nie jest niezalezna eksperymentalnie), wiec potwierdza powtarzalnosc struktury, nie zewnetrzna ogolnosc na inne urzadzenie.
