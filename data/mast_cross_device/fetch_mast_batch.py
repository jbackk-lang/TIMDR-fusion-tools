"""Pobiera surowe chunki magnetics/ip + magnetics/time dla zamrozonej probki strzalow MAST.
Regula probki (zamrozona PRZED jakimkolwiek uruchomieniem detektorow na MAST):
co 20. strzal z numerycznie posortowanej listy mast/level2/shots (indeksy 0,20,40,...).
Wznawialny: pomija juz pobrane strzaly. Uruchom: python fetch_mast_batch.py
"""
import s3fs, os, hashlib, sys
from concurrent.futures import ThreadPoolExecutor

fs = s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": "https://s3.echo.stfc.ac.uk"})
BASE = "mast/level2/shots"
OUT = "raw_mast_batch"
STEP = 20
ARRS = ["magnetics/ip", "magnetics/time"]

shots = sorted(int(p.split("/")[-1].split(".")[0]) for p in fs.ls(BASE) if p.endswith(".zarr"))
sample = shots[::STEP]
with open("shot_list_frozen.txt", "w") as fh:
    fh.write("\n".join(map(str, sample)))
sha = hashlib.sha256("\n".join(map(str, sample)).encode()).hexdigest()
print("strzalow w bucketcie:", len(shots), "| w probce:", len(sample), "| sha256 listy:", sha)

def fetch(shot):
    root = f"{BASE}/{shot}.zarr"
    done_flag = os.path.join(OUT, str(shot), "_done")
    if os.path.exists(done_flag):
        return shot, "skip"
    try:
        for a in ARRS:
            for f in fs.find(f"{root}/{a}"):
                rel = f[len(root) + 1:]
                dst = os.path.join(OUT, str(shot), *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as fh:
                    fh.write(fs.cat(f))
        open(done_flag, "w").close()
        return shot, "ok"
    except Exception as e:
        return shot, f"blad: {type(e).__name__}: {str(e)[:80]}"

os.makedirs(OUT, exist_ok=True)
n_ok = n_skip = 0
fails = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, (shot, st) in enumerate(ex.map(fetch, sample), 1):
        if st == "ok": n_ok += 1
        elif st == "skip": n_skip += 1
        else: fails.append((shot, st))
        if i % 50 == 0:
            print(f"{i}/{len(sample)}  ok={n_ok} skip={n_skip} bledy={len(fails)}", flush=True)
print("KONIEC. ok:", n_ok, "pominiete:", n_skip, "bledy:", len(fails))
for f in fails[:30]:
    print(" ", f)
