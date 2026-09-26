# Audyt twierdzeń README o MAST — pre-rejestracja reguł (pilotaż AI-Core)

Status: ZAMROŻONE przed pierwszym uruchomieniem audytu. Zapisane razem z kartami twierdzeń (`claims_mast.py`),
hashe w `CLAIM_AUDIT_PREREG_HASHES.txt`.
Zastrzeżenie: audytor znał wcześniej pliki `summary.txt` i `summary2.txt` (pisał je). Pre-rejestracja dotyczy reguł audytu
i tolerancji, nie ukrycia danych przed audytorem.

## Zakres
README.md: sekcja „### Walidacja cross-device na MAST (bez etykiet)” (do linii `---`) oraz punkt „Walidacja na MAST”
w „Zakres i ograniczenia”. Nic poza tym (TCABR nie jest w pilotażu).

## Reguły (wzorowane na weryfikacji twierdzeń w TIMeDR-MUZ)
- R1 Dowód. Każde twierdzenie ma kartę: dokładny cytat z README, pliki źródłowe i funkcję, która PRZELICZA wartość z surowych
  wyników (`results.csv`, `results2.csv`, skrypty, pre-rejestracje), a nie przepisuje jej z `summary*.txt`.
  Werdykty: POTWIERDZONE (przeliczenie zgodne), SPRZECZNE (przeliczenie przeczy), NIEROZSTRZYGNIĘTE (nie da się sprawdzić
  z plików), UDOKUMENTOWANE (twierdzenie o zakresie/źródle, oparte na zapisie w pre-rejestracji, bez przeliczenia).
- R2 Tolerancje. Liczba z „ok.”: czasy ±15% względnie; odsetki ±1,0 pp gdy podane z miejscem po przecinku, ±2,0 pp gdy
  całkowite. Liczba bez „ok.”: zgodność do pokazanej precyzji. Twierdzenie o obu próbkach musi zachodzić w każdej z nich.
- R3 Pokrycie. Każda liczba w zakresie (poza częściami identyfikatorów, np. `level2`) musi należeć do cytatu jakiejś karty.
  Liczba bez karty = NIEPOKRYTA.
- R4 Świeżość. Hash `model_j/model_j_detector.py` i skryptów uruchomieniowych równy hashom zamrożonym w
  `PREREGISTRATION_HASHES.txt` / `PREREGISTRATION_2_HASHES.txt`. Niezgodność = wyniki nieaktualne (NIEROZSTRZYGNIĘTE).
- R5 Kompletność. Jeśli w katalogu dowodów jest pre-rejestrowane kryterium z wynikiem NIESPEŁNIONE albo kryteria wyprowadzone
  post hoc z danych, zakres README musi o tym wspominać (wzorzec: niespełn / nie spełni / post hoc / eksplorac / wyprowadz).
  Brak = BRAK KOMPLETNOŚCI.
- R6 Kotwica czasu. Twierdzenie „zamrożone przed uruchomieniem” jest POTWIERDZONE tylko, gdy plik pre-rejestracji trafił do
  gita w commicie wcześniejszym niż plik wyników. Ten sam commit = NIEROZSTRZYGNIĘTE (zamrożenie tylko deklarowane
  znacznikiem `frozen_at_utc`; integralność hashy sprawdzana osobno).
- R7 Sformułowania. (a) Zakazane dla MAST (z pre-rejestracji: „szybki quench != dysrupcja”): zdanie przypisujące szybkiemu
  trybowi/zanikowi status dysrupcji/zakłócenia, bez „nie wiadomo / czy / nie oznacza” w 40 znakach przed nim. (b) Słowa
  bezwzględne („tak samo”, „zawsze”, „nigdy”, „dowodzi”, „udowodni”, „100%”): jeśli dowód pokazuje zgodność w tolerancji,
  a nie równość — zalecenie złagodzenia (nie zmienia werdyktu karty).
- R8 Brak związku. „Nie wykazał związku” = dokładny test Fishera (dwustronny) na tabeli 2x2 (bridge_detector wykrył coś x
  is_fast) daje p > 0,05 w każdej próbce. Raportowana też różnica odsetków.
- R9 Dwumodalność przeliczana niezależnie od sklearn: EM mieszaniny Gaussa w log10(d [ms]) w NumPy (10 startów, ziarno 0);
  kryteria jak K4 z PREREGISTRATION_2.md (ΔBIC > 10, wagi ≥ 0,20, stosunek średnich ≥ 5).

## Wynik audytu
Raport `CLAIM_AUDIT.md`. Audyt NIE zmienia README; zalecenia poprawek są osobnym krokiem.
