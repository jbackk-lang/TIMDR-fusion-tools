"""Karty twierdzeń README o MAST dla tools/claim_audit.py (reguły: CLAIM_AUDIT_PREREG.md).

Każda karta przelicza wartość z surowych wyników (results*.csv, skrypty, pliki pre-rejestracji), nie z summary*.txt.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent
REPO = D.parent.parent
sys.path.insert(0, str(REPO / "tools"))
from claim_audit import (POTWIERDZONE, SPRZECZNE, NIEROZSTRZYGNIETE, UDOKUMENTOWANE, Claim, Result,  # noqa: E402
                         fisher_exact, git_first_commit, sha256, within)

TITLE = "README → sekcja MAST (TIMDR-fusion-tools)"
README = "README.md"
PREREG = "data/mast_cross_device/CLAIM_AUDIT_PREREG.md"
OUTPUT = "CLAIM_AUDIT.md"
SCOPES = [(r"^### Walidacja cross-device na MAST", r"^---"), (r"^- Walidacja na MAST", r"^- ")]


# --------------------------------------------------------------------------- dane
def durations_ms(sample: int) -> pd.Series:
    df = pd.read_csv(D / ("results.csv" if sample == 1 else "results2.csv"))
    if "valid" in df:
        df = df[df.valid]
    return df.quench_duration_s.dropna() * 1e3


def results(sample: int) -> pd.DataFrame:
    df = pd.read_csv(D / ("results.csv" if sample == 1 else "results2.csv"))
    return df[df.valid] if "valid" in df else df


def _ll_gauss(x, mu, var):
    return -0.5 * (np.log(2 * np.pi * var) + (x - mu) ** 2 / var)


def gmm_k4(d_ms: pd.Series, n_init: int = 10, seed: int = 0) -> dict:
    """R9: EM mieszaniny 2 Gaussow w log10(d) w NumPy; BIC jak w sklearn (p = 3k - 1)."""
    x = np.log10(d_ms.values)
    n = x.size
    ll1 = _ll_gauss(x, x.mean(), x.var()).sum()
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_init):
        mu = rng.choice(x, 2, replace=False)
        var = np.full(2, x.var())
        w = np.array([0.5, 0.5])
        prev = -np.inf
        for _ in range(1000):
            lp = np.log(w) + np.stack([_ll_gauss(x, mu[k], var[k]) for k in range(2)], 1)
            m = lp.max(1, keepdims=True)
            ll = float((m[:, 0] + np.log(np.exp(lp - m).sum(1))).sum())
            r = np.exp(lp - m)
            r /= r.sum(1, keepdims=True)
            nk = r.sum(0)
            w, mu = nk / n, (r * x[:, None]).sum(0) / nk
            var = np.maximum((r * (x[:, None] - mu) ** 2).sum(0) / nk, 1e-6)
            if ll - prev < 1e-9:
                break
            prev = ll
        if best is None or ll > best[0]:
            best = (ll, mu.copy(), w.copy())
    ll2, mu, w = best
    o = np.argsort(mu)
    bic1, bic2 = -2 * ll1 + 2 * np.log(n), -2 * ll2 + 5 * np.log(n)
    means = 10 ** mu[o]
    return {"dbic": bic1 - bic2, "means": means, "w": w[o], "ratio": means[1] / means[0]}


def k4_ok(g) -> bool:
    return g["dbic"] > 10 and g["w"].min() >= 0.20 and g["ratio"] >= 5


def pct(x) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


def hashes_from_files() -> dict[str, str]:
    """Zamrozone hashe z PREREGISTRATION_HASHES*.txt, zmapowane na sciezki w repo (pomija pliki spoza repo)."""
    known = {"model_j_detector.py": "model_j/model_j_detector.py"}
    out = {}
    for f in ("PREREGISTRATION_HASHES.txt", "PREREGISTRATION_2_HASHES.txt"):
        for line in (D / f).read_text(encoding="utf-8").splitlines():
            toks = line.split()
            h = next((t for t in toks if re.fullmatch(r"[0-9a-f]{64}", t)), None)
            name = next((Path(t).name for t in toks if t != h and not t.startswith("frozen")), None)
            if not h or not name:
                continue
            rel = known.get(name, f"data/mast_cross_device/{name}")
            if (REPO / rel).exists():
                out[rel] = h
    return out


FROZEN = hashes_from_files()


def script_dict(script: str, name: str) -> dict:
    tree = ast.parse((D / script).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
            return {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
    raise KeyError(name)


# --------------------------------------------------------------------------- karty
def c_code():
    now, frozen = sha256(REPO / "model_j/model_j_detector.py"), FROZEN.get("model_j/model_j_detector.py")
    ok = now == frozen
    return Result(POTWIERDZONE if ok else SPRZECZNE, f"sha256 {now[:12]}",
                  "zgodny z hashem zamrożonym w obu pre-rejestracjach" if ok else f"zamrożony {str(frozen)[:12]}")


def c_samples():
    s1 = (D / "shot_list_frozen.txt").read_text().split()
    s2 = (D / "shot_list_frozen2.txt").read_text().split()
    r1, r2 = len(results(1)), len(results(2))
    common = len(set(s1) & set(s2))
    ok = len(s1) == len(s2) == r1 == r2 == 579 and common == 0
    return Result(POTWIERDZONE if ok else SPRZECZNE, f"listy {len(s1)}/{len(s2)}, wyniki {r1}/{r2}, wspólne {common}")


def c_signal():
    ok = all("magnetics/ip" in (D / s).read_text(encoding="utf-8") for s in ("run_mast_frozen.py", "run_mast_frozen2.py"))
    return Result(POTWIERDZONE if ok else SPRZECZNE, "oba skrypty czytają magnetics/ip" if ok else "brak w skrypcie")


def c_params():
    dt = float(pd.concat([results(1).dt, results(2).dt]).median())
    def conv(n, odd):
        x = n * 4e-6 / dt
        return max(1, int(2 * round((x - 1) / 2) + 1) if odd else int(round(x)))
    expected = {"smooth_window": conv(51, True), "exclude_start": conv(2000, False),
                "long_window": conv(1250, False), "short_window": conv(1001, True)}
    got = {}
    for s in ("run_mast_frozen.py", "run_mast_frozen2.py"):
        qd, br = script_dict(s, "QD"), script_dict(s, "BR")
        got[s] = {"smooth_window": qd["smooth_window"], "exclude_start": qd["exclude_start"],
                  "long_window": br["long_window"], "short_window": br["short_window"],
                  "exclude_start_br": br["exclude_start"]}
    ok = all(all(g[k] == v for k, v in expected.items()) and g["exclude_start_br"] == expected["exclude_start"]
             for g in got.values())
    val = ", ".join(f"{k}={v}" for k, v in expected.items())
    return Result(POTWIERDZONE if ok else SPRZECZNE, f"dt={dt * 1e3:.1f} ms → {val}".replace(".", ","),
                  "reguła TCABR 4 µs → MAST z PREREGISTRATION.md, zgodna z oboma skryptami" if ok else str(got))


def c_frozen():
    bad = [p for p, h in FROZEN.items() if sha256(REPO / p) != h]
    anchors = []
    for pre, res in (("PREREGISTRATION.md", "results.csv"), ("PREREGISTRATION_2.md", "results2.csv")):
        a, b = git_first_commit(REPO, D / pre), git_first_commit(REPO, D / res)
        anchors.append((pre, a, b, a is not None and b is not None and a[1] < b[1]))
    if bad:
        return Result(SPRZECZNE, "hashe niezgodne", ", ".join(bad))
    if all(x[3] for x in anchors):
        return Result(POTWIERDZONE, "hashe zgodne, pre-rejestracje w gicie przed wynikami")
    same = "; ".join(f"{p}: commit {a[0] if a else '-'} = wyniki {b[0] if b else '-'}" for p, a, b, ok in anchors if not ok)
    return Result(NIEROZSTRZYGNIETE, f"{len(FROZEN)} hashy zgodnych",
                  f"R6: pre-rejestracja i wyniki w tym samym commicie ({same}); moment zamrożenia tylko deklarowany "
                  f"znacznikiem frozen_at_utc")


def c_bimodal():
    g = [gmm_k4(durations_ms(s)) for s in (1, 2)]
    ok = all(k4_ok(x) for x in g)
    val = "; ".join(f"próbka {i + 1}: ΔBIC {x['dbic']:.0f}, wagi {x['w'][0]:.2f}/{x['w'][1]:.2f}, "
                    f"stosunek {x['ratio']:.0f}" for i, x in enumerate(g))
    return Result(POTWIERDZONE if ok else SPRZECZNE, val.replace(".", ","), "EM w NumPy, kryteria K4")


def c_modes():
    g = [gmm_k4(durations_ms(s)) for s in (1, 2)]
    ok = all(2 * 0.85 <= x["means"][0] <= 3 * 1.15 and within(50, x["means"][1], approx=True) for x in g)
    val = "; ".join(f"próbka {i + 1}: {x['means'][0]:.2f} i {x['means'][1]:.1f} ms" for i, x in enumerate(g))
    return Result(POTWIERDZONE if ok else SPRZECZNE, val.replace(".", ","), "tolerancja ±15%")


def c_gap():
    fr = [float(((d >= 4) & (d <= 15)).mean()) for d in (durations_ms(1), durations_ms(2))]
    ok = all(within(4.5, 100 * f, approx=True, pct=True, decimals=1) for f in fr)
    return Result(POTWIERDZONE if ok else SPRZECZNE, f"próbka 1: {pct(fr[0])}, próbka 2: {pct(fr[1])}",
                  "tolerancja ±1,0 pp")


def c_repeat():
    g = [gmm_k4(durations_ms(s)) for s in (1, 2)]
    fr = [float(((d >= 4) & (d <= 15)).mean()) for d in (durations_ms(1), durations_ms(2))]
    ok = all(k4_ok(x) for x in g) and all(f <= 0.10 for f in fr)
    return Result(POTWIERDZONE if ok else SPRZECZNE, "K4 i przerwa ≤ 10% w obu próbkach" if ok else "nie w obu",
                  "próbka 1 była eksploracyjna (kryteria z niej wyprowadzone), potwierdzenie daje tylko próbka 2")


def c_threshold():
    thr = [script_dict(s, "QD") and float(re.search(r"FAST_THR\s*=\s*([\d.]+)", (D / s).read_text()).group(1))
           for s in ("run_mast_frozen.py", "run_mast_frozen2.py")]
    diffs = [abs(float((d < 15).mean()) - float((d < 7.7).mean())) for d in (durations_ms(1), durations_ms(2))]
    ok = all(t == 0.015 for t in thr) and all(x <= 0.05 for x in diffs)
    return Result(POTWIERDZONE if ok else SPRZECZNE,
                  f"różnica odsetka szybkich 15 vs 7,7 ms: {pct(diffs[0])} i {pct(diffs[1])} (tolerancja K5 ≤ 5 pp)",
                  "zgodność w tolerancji, nie równość - patrz R7b")


def c_scope():
    ok = "NIE mierzy trafności" in (D / "PREREGISTRATION.md").read_text(encoding="utf-8")
    return Result(UDOKUMENTOWANE if ok else NIEROZSTRZYGNIETE, "zapis w PREREGISTRATION.md",
                  "zakres zadeklarowany z góry")


def c_labels():
    ok = all("AccessDenied" in (D / f).read_text(encoding="utf-8") for f in ("PREREGISTRATION.md", "PREREGISTRATION_2.md"))
    return Result(UDOKUMENTOWANE if ok else NIEROZSTRZYGNIETE, "zapis w obu pre-rejestracjach",
                  "stanu dostępu do level2/defuse nie da się sprawdzić z plików (wymaga sieci)")


def c_fast():
    fr = [float((d < 15).mean()) for d in (durations_ms(1), durations_ms(2))]
    ok = all(within(65, 100 * f, approx=True, pct=True) for f in fr)
    return Result(POTWIERDZONE if ok else SPRZECZNE, f"próbka 1: {pct(fr[0])}, próbka 2: {pct(fr[1])}",
                  "tolerancja ±2,0 pp")


def c_bridge():
    out, ok = [], True
    for s in (1, 2):
        df = results(s).dropna(subset=["quench_duration_s"])
        fire, fast = df.n_bridge > 0, df.is_fast.astype(str) == "True"
        a, b = int((fire & fast).sum()), int((fire & ~fast).sum())
        c, d = int((~fire & fast).sum()), int((~fire & ~fast).sum())
        p = fisher_exact(a, b, c, d)
        diff = a / (a + c) - b / (b + d)
        ok &= p > 0.05
        out.append(f"próbka {s}: {pct(a / (a + c))} vs {pct(b / (b + d))} (różnica {diff * 100:+.1f} pp), p = {p:.2f}")
    return Result(POTWIERDZONE if ok else SPRZECZNE, "; ".join(out).replace("p = 0.", "p = 0,").replace("pp), ", "pp), "),
                  "dokładny test Fishera; odsetek strzałów z wykryciem mostu wśród szybkich vs wolnych")


def c_limits_phasespace():
    pre = (D / "PREREGISTRATION.md").read_text(encoding="utf-8")
    used = any("phasespace" in (D / s).read_text(encoding="utf-8") for s in ("run_mast_frozen.py", "run_mast_frozen2.py"))
    ok = "co 5 ms" in pre and "NaN" in pre and not used
    return Result(UDOKUMENTOWANE if ok else NIEROZSTRZYGNIETE, "PREREGISTRATION.md: 155 pkt co 5 ms, część NaN",
                  "żaden skrypt MAST nie wywołuje phasespace_funnel_ratio")


CLAIMS = [
    Claim("M1", "uruchomione bez zmian kodu", c_code),
    Claim("M2", "na dwóch rozłącznych próbkach po 579 strzałów MAST", c_samples),
    Claim("M3", "(`magnetics/ip`", c_signal),
    Claim("M4", "parametry okienkowe przeliczone na czas fizyczny", c_params),
    Claim("M5", "kryteria zamrożone przed uruchomieniem", c_frozen),
    Claim("M6", "rozkład czasu zaniku jest dwumodalny", c_bimodal),
    Claim("M7", "(ok. 2–3 ms i ok. 50 ms", c_modes),
    Claim("M8", "przerwa 4–15 ms zawiera ok. 4,5% strzałów", c_gap),
    Claim("M9", "i powtarzalny w obu próbkach", c_repeat),
    Claim("M10", "próg 15 ms z TCABR działa tak samo jak 7,7 ms", c_threshold),
    Claim("M11", "To opis struktury rozkładu, nie trafność klasyfikacji", c_scope),
    Claim("M12", "dla MAST nie ma dostępnych etykiet dysrupcji (`level2/defuse`: AccessDenied)", c_labels),
    Claim("M13", "szybki tryb (ok. 65% strzałów)", c_fast),
    Claim("M14", "`bridge_detector()` nie wykazał na MAST związku z `is_fast_quench()`", c_bridge),
    Claim("M15", "pokazuje powtarzalną dwumodalność czasu zaniku, nie skuteczność klasyfikacji na MAST", c_repeat),
    Claim("M16", "`phasespace_funnel_ratio()` nie był na MAST testowany (Vloop z rekonstrukcji EFIT ma zbyt rzadkie "
                 "próbkowanie, 5 ms, z lukami)", c_limits_phasespace),
]

COMPLETENESS = [
    ("data/mast_cross_device/summary.txt", r"NIESPELNIONE", "pre-rejestrowane kryterium K1 w próbce 1 niespełnione"),
    ("data/mast_cross_device/PREREGISTRATION_2.md", r"WYPROWADZONE", "kryteria K1', K4, K5 wyprowadzone z próbki 1 (post hoc)"),
]
COMPLETENESS_REQUIRED = r"niespełn|nie spełni|post hoc|eksplorac|wyprowadz"
ANCHORS = [("data/mast_cross_device/PREREGISTRATION.md", "data/mast_cross_device/results.csv"),
           ("data/mast_cross_device/PREREGISTRATION_2.md", "data/mast_cross_device/results2.csv")]
FORBIDDEN = [(r"szybki\w*\s+(tryb|zanik\w*|quench\w*)[^.]{0,40}?\b(to|są|oznacza)\b[^.]{0,20}?(dysrupc|zakłóce)\w*",
              r"nie wiadomo|czy|nie oznacza|!=", "pre-rejestracja: szybki quench != dysrupcja, brak etykiet")]
ABSOLUTE = [(r"\btak samo\b", "dowód to zgodność w tolerancji, nie równość - podaj różnicę"),
            (r"\bzawsze\b|\bnigdy\b", "słowo bezwzględne - sprawdź, czy dowód to pokrywa"),
            (r"\bdowodzi\b|\budowodni\w*", "„dowodzi” wymaga dowodu, nie testu statystycznego"),
            (r"(?<!\d)100 ?%", "100% - sprawdź liczność i wyjątki")]
