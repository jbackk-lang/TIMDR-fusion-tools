# Próbka 1 — odtworzenie z surowych danych

Pierwotny przebieg próbki 1 (`run_mast_frozen.py`) czytał plik pośredni `/tmp/w/data.pkl`, którego kod tworzący nie był
w repozytorium (luka wykryta audytem twierdzeń, `CLAIM_AUDIT.md`, karta M3). Próbkę 1 przeliczono więc od surowych chunków
zarr loaderem z `run_mast_frozen2.py` (ten sam kod detektora, te same zamrożone parametry i reguła QC R1):

```
RAW_DIR=raw_mast_batch OUT_TAG=1_repro python run_mast_frozen2.py
python compare_repro.py
```

- surowe dane: `raw_mast_batch.zip`, sha256 68f9eb86…4e69 (zgodny z PREREGISTRATION_HASHES.txt), 579 strzałów;
- detektor: `model_j/model_j_detector.py`, sha256 908ee2f2…1734 (niezmieniony);
- środowisko: Python 3.11, NumPy 2.4, pandas 3.0, zstandard 0.25 (dekodowanie zstd poza Windows — Device Guard blokuje
  niepodpisane biblioteki natywne);
- wynik `results1_repro.csv` (sha256 fe918dda…eb48): **0 różnic** z `results.csv` we wszystkich kolumnach
  (flipped, n, is_fast, n_bridge, dt, ipmax, quench_duration_s), 579/579 strzałów poprawnych.

Pełny łańcuch próbki 1 da się więc odtworzyć z plików w repozytorium i surowego archiwum.
