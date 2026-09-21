"""Test potwierdzajacy (probka 2) - ZAMROZONE parametry i kryteria, patrz PREREGISTRATION_2.md.
Nie modyfikuje kodu detektorow. Wejscie: katalog z surowymi chunkami zarr (RAW_DIR), wyjscie: results2.csv + summary2.txt.
Uzycie: RAW_DIR=/sciezka/raw_mast_batch2 DETECTOR_ROOT=/sciezka/TIMDR-fusion-tools python run_mast_frozen2.py
"""
import os, sys, json
import numpy as np
import pandas as pd
import zstandard

DETECTOR_ROOT = os.environ.get("DETECTOR_ROOT", "/mnt/user-data/uploads/Downloads/a/TIMDR-fusion-tools")
RAW_DIR = os.environ.get("RAW_DIR", "/tmp/w2/raw_mast_batch2")
TAG = os.environ.get("OUT_TAG", "2")
sys.path.insert(0, DETECTOR_ROOT)
from model_j.model_j_detector import bridge_detector, quench_duration, is_fast_quench

# ---- ZAMROZONE PARAMETRY (identyczne jak w run_mast_frozen.py) ----
QD = dict(fraction_high=0.70, fraction_low=0.10, smooth_window=1, exclude_start=40)
FAST_THR = 0.015
BR = dict(long_window=25, drop_fraction=0.30, short_window=21, short_threshold=5.0, exclude_start=40)
# ---- ZAMROZONE KRYTERIA ----
GAP = (0.004, 0.015); K1_MAX = 0.10          # K1': odsetek d w [4, 15] ms <= 10%
K2_MIN = 0.80                                 # K2: pokrycie
K4_DBIC = 10.0; K4_MINW = 0.20; K4_RATIO = 5.0  # K4: dwumodalnosc (GMM w log10 d)
K5_ALT_THR = 0.0077; K5_MAX_DIFF = 0.05      # K5: odpornosc na prog 15 ms vs 7,7 ms

dctx = zstandard.ZstdDecompressor()


def load_arr(d):
    m = json.load(open(d + "/zarr.json"))
    shp = m["shape"]
    assert len(shp) == 1, shp
    cs = m["chunk_grid"]["configuration"]["chunk_shape"][0]
    codecs = [c["name"] for c in m["codecs"]]
    assert set(codecs) <= {"bytes", "zstd"}, codecs
    dt = np.dtype(m["data_type"]).newbyteorder("<")
    n = shp[0]
    out = np.full(n, np.nan)
    for k in range(-(-n // cs) if n else 0):
        p = f"{d}/c/{k}"
        if not os.path.exists(p):
            continue
        raw = open(p, "rb").read()
        b = dctx.decompress(raw, max_output_size=10**9) if "zstd" in codecs else raw
        a = np.frombuffer(b, dtype=dt)
        out[k * cs:k * cs + a.size] = a
    return out


rows = []
for sd in sorted(os.listdir(RAW_DIR), key=int):
    shot = int(sd)
    r = dict(shot=shot, valid=False, reason="")
    try:
        ip = load_arr(f"{RAW_DIR}/{sd}/magnetics/ip")
        t = load_arr(f"{RAW_DIR}/{sd}/magnetics/time")
        if ip.size != t.size or ip.size <= 200:
            raise ValueError("dlugosc")
        if np.isnan(ip).any() or np.isnan(t).any():
            raise ValueError("NaN")
        d = np.diff(t)
        dt = float(np.median(d))
        if not (np.max(np.abs(d - dt)) / dt < 0.01):
            raise ValueError("nierownomierny dt")
        x = ip.astype(float)
        flipped = bool(abs(x[40:].min()) > abs(x[40:].max()))   # regula QC R1
        if flipped:
            x = -x
        r.update(valid=True, flipped=flipped, dt=dt, n=x.size, ipmax=float(x.max()))
        dq = quench_duration(x, dt=dt, **QD)
        r["quench_duration_s"] = dq
        r["is_fast"] = is_fast_quench(x, dt=dt, duration_threshold=FAST_THR, **QD)
        r["n_bridge"] = int(bridge_detector(x, **BR).size)
    except Exception as e:
        r["reason"] = f"{type(e).__name__}:{str(e)[:50]}"
    rows.append(r)
df = pd.DataFrame(rows)
df.to_csv(f"results{TAG}.csv", index=False)

out = []
N = len(df)
valid = df[df.valid]
cov_df = valid.dropna(subset=["quench_duration_s"])
d = cov_df.quench_duration_s
out.append(f"shots w probce={N} poprawne={len(valid)} niepoprawne={N - len(valid)} flipped_sign={int(valid.flipped.sum())}")
if N - len(valid):
    out.append("niepoprawne: " + str(df[~df.valid][["shot", "reason"]].values.tolist()))
cov = len(cov_df) / N
out.append(f"K2 pokrycie: {len(cov_df)}/{N} = {cov:.3f} (prog >= {K2_MIN}) -> {'SPELNIONE' if cov >= K2_MIN else 'NIESPELNIONE'}")
gapfrac = float(((d >= GAP[0]) & (d <= GAP[1])).mean())
out.append(f"K1' odsetek d w [4, 15] ms: {gapfrac:.3f} (prog <= {K1_MAX}) -> {'SPELNIONE' if gapfrac <= K1_MAX else 'NIESPELNIONE'}")

from sklearn.mixture import GaussianMixture
X = np.log10(d.values * 1e3).reshape(-1, 1)
g1 = GaussianMixture(1, n_init=10, random_state=0).fit(X)
g2 = GaussianMixture(2, n_init=10, random_state=0).fit(X)
order = np.argsort(g2.means_.ravel())
means = 10 ** g2.means_.ravel()[order]; w = g2.weights_[order]
dbic = g1.bic(X) - g2.bic(X)
k4 = (dbic > K4_DBIC) and (w.min() >= K4_MINW) and (means[1] / means[0] >= K4_RATIO)
out.append(f"K4 GMM: BIC1-BIC2={dbic:.1f} (prog > {K4_DBIC}), skladniki(ms)={means.round(2).tolist()}, wagi={w.round(2).tolist()}, "
           f"stosunek srednich={means[1] / means[0]:.1f} (prog >= {K4_RATIO}), min waga >= {K4_MINW} -> {'SPELNIONE' if k4 else 'NIESPELNIONE'}")
f15 = float((d < FAST_THR).mean()); f77 = float((d < K5_ALT_THR).mean())
out.append(f"K5 odsetek szybkich: prog 15 ms={f15:.3f}, prog 7,7 ms={f77:.3f}, roznica={abs(f15 - f77):.3f} (prog <= {K5_MAX_DIFF}) -> "
           f"{'SPELNIONE' if abs(f15 - f77) <= K5_MAX_DIFF else 'NIESPELNIONE'}")
lo, hi = np.log10(means)
grid = np.linspace(lo, hi, 2000); post = g2.predict_proba(grid.reshape(-1, 1))[:, order]
out.append(f"opis: granica 50/50 miedzy skladnikami = {10 ** grid[np.argmin(np.abs(post[:, 0] - post[:, 1]))]:.2f} ms")
q = (d.quantile([0, .05, .25, .5, .75, .95, 1]) * 1e3)
out.append("kwantyle d [ms]: " + ", ".join(f"{k:.2f}->{v:.1f}" for k, v in q.items()))
bins = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 60, 100, 200, 5000]
out.append("histogram [ms]: " + "; ".join(f"{i}:{v}" for i, v in pd.cut(d * 1e3, bins=bins).value_counts().sort_index().items()))
cov_df = cov_df.assign(bin=pd.cut(cov_df.shot, [11000, 14000, 17000, 20000, 23000, 26000, 31000]))
out.append("odsetek szybkich wg kampanii:\n" + cov_df.groupby("bin", observed=True).agg(n=("shot", "size"), fast=("is_fast", "mean")).round(3).to_string())
out.append("bridge_detector vs is_fast:\n" + pd.crosstab(cov_df.n_bridge > 0, cov_df.is_fast.astype(str)).to_string())
open(f"summary{TAG}.txt", "w").write("\n".join(out))
print("\n".join(out))
