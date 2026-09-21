"""Jednorazowe uruchomienie ZAMROZONYCH detektorow na probce MAST (patrz PREREGISTRATION.md + ADDENDUM_1).
Nie modyfikuje kodu detektorow. Wejscie: /tmp/w/data.pkl (t, ip) per strzal. Wyjscie: results.csv + summary.txt
"""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/user-data/uploads/Downloads/a/TIMDR-fusion-tools")
from model_j.model_j_detector import bridge_detector, quench_duration, is_fast_quench

# --- ZAMROZONE PARAMETRY (PREREGISTRATION.md, regula przenoszenia TCABR 4us -> MAST 200us) ---
QD = dict(fraction_high=0.70, fraction_low=0.10, smooth_window=1, exclude_start=40)
FAST_THR = 0.015
BR = dict(long_window=25, drop_fraction=0.30, short_window=21, short_threshold=5.0, exclude_start=40)
K1_WINDOW = (0.0075, 0.030); K1_MAX_FRAC = 0.10; K2_MIN_COVERAGE = 0.80

data = pickle.load(open("/tmp/w/data.pkl", "rb"))
rows = []
for shot in sorted(data):
    t, ip = data[shot]
    x = np.asarray(ip, float)
    flipped = bool(abs(np.nanmin(x)) > abs(np.nanmax(x)))   # regula QC R1 (ADDENDUM_1)
    if flipped:
        x = -x
    dt = float(np.median(np.diff(t)))
    d = quench_duration(x, dt=dt, **QD)
    f = is_fast_quench(x, dt=dt, duration_threshold=FAST_THR, **QD)
    br = bridge_detector(x, **BR)
    rows.append(dict(shot=shot, flipped=flipped, dt=dt, n=x.size, ipmax=float(x.max()),
                     quench_duration_s=d, is_fast=f, n_bridge=int(br.size)))
df = pd.DataFrame(rows); df.to_csv("results.csv", index=False)

out = []
N = len(df); defined = df.dropna(subset=["quench_duration_s"])
cov = len(defined) / N
out.append(f"shots={N} flipped_sign={int(df.flipped.sum())}")
out.append(f"K2 pokrycie (quench_duration != None): {len(defined)}/{N} = {cov:.3f}  (prog >= {K2_MIN_COVERAGE}) -> {'SPELNIONE' if cov >= K2_MIN_COVERAGE else 'NIESPELNIONE'}")
d = defined.quench_duration_s
inwin = ((d >= K1_WINDOW[0]) & (d <= K1_WINDOW[1])).mean() if len(d) else float('nan')
out.append(f"K1 odsetek d w [7.5,30] ms: {inwin:.3f}  (prog <= {K1_MAX_FRAC}) -> {'SPELNIONE' if inwin <= K1_MAX_FRAC else 'NIESPELNIONE'}")
out.append(f"is_fast=True: {int((df.is_fast==True).sum())}, False: {int((df.is_fast==False).sum())}, None: {int(df.is_fast.isna().sum())}")
q = d.quantile([0, .05, .1, .25, .5, .75, .9, .95, 1]) * 1e3
out.append("kwantyle quench_duration [ms]: " + ", ".join(f"{k:.2f}->{v:.1f}" for k, v in q.items()))
bins = [0, 1, 2, 3, 5, 7.5, 15, 30, 60, 120, 1e9]
h = pd.cut(d * 1e3, bins=bins).value_counts().sort_index()
out.append("histogram [ms]: " + "; ".join(f"{i}:{v}" for i, v in h.items()))
out.append("K3 bridge_detector: liczba wykryc/strzal: " + str(df.n_bridge.describe().round(1).to_dict()))
out.append("K3 tabela (bridge fires? x is_fast):")
out.append(pd.crosstab(df.n_bridge > 0, df.is_fast.astype(str), dropna=False).to_string())
open("summary.txt", "w").write("\n".join(out)); print("\n".join(out))
