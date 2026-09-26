"""Porownuje results.csv (probka 1, pierwotny przebieg z /tmp/w/data.pkl) z results1_repro.csv
(ta sama probka przeliczona loaderem z run_mast_frozen2.py prosto z surowych chunkow zarr).
Uzycie: python compare_repro.py  -> liczba roznic w kazdej kolumnie (oczekiwane: 0)."""
import numpy as np
import pandas as pd

a = pd.read_csv("results.csv")
b = pd.read_csv("results1_repro.csv")
assert set(a.shot) == set(b.shot) and len(a) == len(b), "rozne listy strzalow"
m = a.merge(b, on="shot", suffixes=("_o", "_r"))
total = 0
for c in ["flipped", "n", "is_fast", "n_bridge"]:
    k = int((m[c + "_o"].astype(str) != m[c + "_r"].astype(str)).sum()); total += k; print(f"{c}: {k}")
for c in ["dt", "ipmax", "quench_duration_s"]:
    x, y = m[c + "_o"], m[c + "_r"]
    k = int(((~(x.isna() & y.isna())) & ~np.isclose(x, y, rtol=1e-9, atol=1e-12)).sum()); total += k; print(f"{c}: {k}")
print("ROZNIC LACZNIE:", total, "| niepoprawnych w repro:", int((~b.valid).sum()))
