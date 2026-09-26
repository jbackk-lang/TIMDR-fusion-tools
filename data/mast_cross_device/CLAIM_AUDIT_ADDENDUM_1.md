# Aneks 1 do CLAIM_AUDIT_PREREG.md (zapisany PRZED drugim uruchomieniem audytu)

Pierwszy audyt: commit 1c7f5c6, raport `CLAIM_AUDIT.md` (sekcja „Analiza rozbieżności” opisuje wyniki post hoc).
Po nim:

1. README (sekcja MAST) poprawione zgodnie z zaleceniami raportu: podane niespełnione K1 i kryteria wyprowadzone post hoc,
   mediany skupień zamiast parametrów GMM, „prawie ten sam podział (różnica 2,4 pp)” zamiast „tak samo”, ujawnione wspólne
   commity pre-rejestracji i wyników, link do odtworzenia próbki 1.
2. Próbka 1 przeliczona z surowych danych loaderem `run_mast_frozen2.py`: `results1_repro.csv`, 0 różnic
   (`REPRODUCTION_SAMPLE1.md`, `compare_repro.py`).
3. Silnik przeniesiony do TIMDR-AI-Core (`claim_audit.py` v0.2, commit 36d5043) i wendorowany (`tools/VENDOR.lock.json`).
   Zmiany reguł względem v0.1:
   - R5: każdy wyzwalacz ma własny wzorzec wymagany w README (v0.1 miał jeden wspólny, więc „post hoc” zaliczało też
     brak informacji o niespełnionym K1);
   - R6: gdy pre-rejestracja i wyniki są w tym samym commicie, a README to opisuje (wzorzec `ANCHOR_DISCLOSURE`), wynik to
     UJAWNIONE zamiast NIEROZSTRZYGNIĘTE. Brak kotwicy czasu nie znika — jest tylko opisany.
4. Karty v1.1 (`claims_mast.py`, lista zmian w nagłówku). Karty zmieniono PO zobaczeniu wyników pierwszego audytu; drugi
   audyt sprawdza zgodność poprawionego README z plikami, nie jest niezależnym testem.

Tolerancje R2, reguły R1, R3, R4, R7 bez zmian.
