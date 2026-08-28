"""
FastAPI wrapper wystawiajacy pipeline fusion-tools (TIMDR + Lambda-tau-rho +
Model J) jako endpoint HTTP, plus prosty dashboard w static/index.html.

Uruchomienie:
    pip install -r requirements.txt
    uvicorn api:app --reload
    (albo po prostu run.bat na Windows)

Endpointy:
    GET  /                 -> dashboard (static/index.html)
    GET  /example           -> metadane wbudowanego przykladowego sygnalu
    POST /analyze            -> uruchamia pipeline na wgranym pliku
                                (CSV albo HDF5) lub na wbudowanym przykladzie
"""
import io
import json
import os
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from latro.latro_core import latro, latro_windowed
from model_j.model_j_detector import model_j
from timdr.timdr_filter import timdr

# load_hdf5() (parsers/hdf5_parser.py) importuje h5py. h5py to zewnetrzny
# pakiet z binarnym rozszerzeniem - jesli jego instalacja/import zawiedzie
# (np. brak pasujacego kola/wheel dla danej wersji Pythona na Windows, albo
# po prostu ktos nie doinstalowal requirements.txt), caly dashboard (w tym
# obsluga CSV, ktora nie ma nic wspolnego z h5py) nie powinien przez to
# przestac dzialac. Import jest wiec opcjonalny - obsluga HDF5 jest
# wylaczana z jasnym komunikatem zamiast wywalac caly serwer przy starcie.
try:
    from parsers.hdf5_parser import load_hdf5
    _HDF5_IMPORT_ERROR = None
except Exception as e:  # pragma: no cover - zalezne od srodowiska
    load_hdf5 = None
    _HDF5_IMPORT_ERROR = str(e)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
EXAMPLE_CSV = os.path.join(DATA_DIR, "w7x_mirnov_example.csv")
STATIC_DIR = os.path.join(REPO_ROOT, "static")

# Zabezpieczenie przed zawieszeniem/zbyt ciezkim wykresem w przegladarce dla
# bardzo dlugich sygnalow. Operacje same w sobie sa O(n) i szybkie nawet dla
# milionow probek, ale rysowanie milionow punktow w Chart.js w przegladarce
# potrafi zawiesic karte przegladarki - ten sam wzorzec co w
# TIMDR-Materials-Design (szybka walidacja rozmiaru zanim zaczniemy liczyc).
MAX_SAMPLES = 200_000

# Nazwy datasetow HDF5 rozpoznawane automatycznie (bez rozrozniania wielkosci liter).
_TIME_NAMES = {"time", "t", "czas"}
_SIGNAL_NAMES = {"signal", "value", "values", "data", "y", "sygnal", "wartosc"}


def _check_size_limit(n_samples):
    if n_samples > MAX_SAMPLES:
        raise HTTPException(
            400,
            f"Sygnal ma {n_samples} probek, limit to {MAX_SAMPLES}. "
            f"Przytnij plik albo zdownsampluj przed wgraniem.",
        )


def _select_hdf5_time_signal(data_dict, dataset_param=None):
    """
    Wybiera (time, signal) z dict {nazwa: array} zwroconego przez load_hdf5().

    HDF5 nie ma ustalonej konwencji "pierwsza kolumna = czas" jak CSV, wiec
    zamiast cicho zgadywac, funkcja:
      1. bierze pod uwage tylko 1-wymiarowe numeryczne datasety,
      2. szuka datasetu nazwanego "time"/"t"/"czas" na os X,
      3. szuka datasetu nazwanego "signal"/"value"/... na sygnal,
      4. jesli nazwy nie pasuja: przy dokladnie jednym pozostalym kandydacie
         uzywa go bez pytania; przy kilku - wybiera pierwszy alfabetycznie,
         ale ZAWSZE zwraca liste wszystkich dostepnych datasetow i informacje
         o tym, co zostalo wybrane, zeby uzytkownik mogl to zweryfikowac albo
         wymusic inny wybor parametrem `dataset`.
      5. jesli nie znaleziono datasetu czasu, generuje indeksy probek jako
         os X i jawnie to raportuje (time_source="synthetic_index").
    """
    candidates = {}
    for name, arr in data_dict.items():
        arr = np.asarray(arr)
        if arr.ndim == 1 and np.issubdtype(arr.dtype, np.number):
            candidates[name] = arr.astype(float)

    if not candidates:
        raise HTTPException(400, "Plik HDF5 nie zawiera zadnego 1-wymiarowego numerycznego datasetu.")

    available = sorted(candidates.keys())

    signal_name = None
    if dataset_param:
        if dataset_param not in candidates:
            raise HTTPException(
                400,
                f"Dataset '{dataset_param}' nie istnieje jako 1D numeryczny dataset. "
                f"Dostepne: {available}",
            )
        signal_name = dataset_param

    time_name = None
    for name in candidates:
        if name.lower() in _TIME_NAMES:
            time_name = name
            break

    if signal_name is None:
        for name in candidates:
            if name == time_name:
                continue
            if name.lower() in _SIGNAL_NAMES:
                signal_name = name
                break

    remaining = [n for n in available if n != time_name]
    ambiguous = False
    if signal_name is None:
        if len(remaining) == 1:
            signal_name = remaining[0]
        elif len(remaining) > 1:
            signal_name = sorted(remaining)[0]
            ambiguous = True
        else:
            raise HTTPException(400, f"Nie znaleziono datasetu sygnalu w pliku HDF5. Dostepne: {available}")

    signal_arr = candidates[signal_name]
    if time_name is not None:
        time_arr = candidates[time_name]
        time_source = f"dataset:{time_name}"
    else:
        time_arr = np.arange(len(signal_arr), dtype=float)
        time_source = "synthetic_index"

    return time_arr, signal_arr, {
        "available_datasets": available,
        "signal_dataset": signal_name,
        "time_dataset": time_name,
        "time_source": time_source,
        "ambiguous": ambiguous and dataset_param is None,
    }


def _describe_result(t, signal_arr, window, reduced, lam, tau, rho, points, rhos_windowed):
    """
    Buduje krotki, deterministyczny opis wyniku po polsku - bez wywolywania
    LLM, tylko z policzonych juz statystyk. Celowo NIE interpretuje wyniku
    fizycznie (patrz zastrzezenie na koncu) - to opisowa statystyka, nie
    diagnoza plazmy.
    """
    x = np.asarray(signal_arr, dtype=float)
    n = len(x)
    xmin, xmax = float(np.min(x)), float(np.max(x))
    k = len(points)
    density = k / n if n else 0.0

    parts = [
        f"Sygnal ma {n} probek, zredukowanych przez TIMDR do {len(reduced)} (okno={window}).",
        f"Wartosci miesza sie w zakresie od {xmin:.4g} do {xmax:.4g} (Lambda = {lam:.4g}, "
        f"tau = {tau:.4g}, rho = {rho:.4g}).",
    ]

    if k == 0:
        parts.append("Model J nie wykryl zadnych punktow skretu przy tym progu.")
    else:
        gap = max(window, 1)
        clusters = [[points[0]]]
        for p in points[1:]:
            if p - clusters[-1][-1] <= gap:
                clusters[-1].append(p)
            else:
                clusters.append([p])

        shown = clusters[:5]
        cluster_desc = ", ".join(
            f"~t={t[c[0]]:.3g}" + (f"..{t[c[-1]]:.3g}" if len(c) > 1 else "")
            for c in shown
        )
        more = f" i {len(clusters) - 5} innych miejscach" if len(clusters) > 5 else ""
        # etykieta oparta na LICZBIE ODREBNYCH KLASTROW (zdarzen), nie na
        # surowej liczbie probek powyzej progu - jedno gwaltowne zdarzenie
        # moze latwo dac kilkanascie sasiadujacych probek nad progiem, wiec
        # sama liczba punktow zawyzalaby wrazenie "duzo zdarzen".
        n_clusters = len(clusters)
        if n_clusters == 1:
            cluster_label = "pojedyncze zdarzenie"
        elif n_clusters <= 5:
            cluster_label = "kilka odrebnych zdarzen"
        elif n_clusters <= 15:
            cluster_label = "kilkanascie odrebnych zdarzen"
        else:
            cluster_label = "wiele odrebnych zdarzen"
        parts.append(
            f"Model J wykryl {k} probek powyzej progu ({density * 100:.2g}% wszystkich probek), "
            f"skupionych w {n_clusters} miejscach w czasie ({cluster_label}): {cluster_desc}{more}."
        )

    if len(rhos_windowed) >= 2:
        q = max(1, len(rhos_windowed) // 4)
        first_q = float(np.mean(rhos_windowed[:q]))
        last_q = float(np.mean(rhos_windowed[-q:]))
        change_pct = (last_q - first_q) / first_q * 100 if first_q > 0 else 0.0
        if abs(change_pct) < 15:
            trend = "wzglednie stabilna w czasie"
        elif change_pct > 0:
            trend = f"rosnie w czasie (o ok. {change_pct:.0f}% od poczatku do konca sygnalu)"
        else:
            trend = f"maleje w czasie (o ok. {abs(change_pct):.0f}% od poczatku do konca sygnalu)"
        parts.append(f"Energia sygnalu (rho) liczona osobno w kolejnych oknach jest {trend}.")

    parts.append(
        "Uwaga: to automatyczny, czysto statystyczny opis (bez interpretacji fizycznej "
        "MHD) - patrz sekcja \"Zakres i ograniczenia\" w README."
    )
    return " ".join(parts)


def _run_pipeline(time_arr, signal_arr, window, threshold, drop_last, extra=None):
    n = len(signal_arr)
    if n == 0:
        raise HTTPException(400, "Sygnal jest pusty.")
    _check_size_limit(n)
    if window < 1:
        raise HTTPException(400, "window musi byc >= 1.")

    reduced = timdr(signal_arr, window=window, drop_last=drop_last)

    t = np.asarray(time_arr, dtype=float)
    dt = (t[-1] - t[0]) / max(n - 1, 1) if n > 1 else 1.0
    reduced_x = (t[0] + (np.arange(len(reduced)) + 0.5) * window * dt).tolist()

    lam, tau, rho = latro(signal_arr)
    lambdas_w, taus_w, rhos_w = latro_windowed(signal_arr, window=window, drop_last=drop_last)
    points = model_j(signal_arr, threshold=threshold)

    description = _describe_result(t, signal_arr, window, reduced, lam, tau, rho, points, rhos_w)

    result = {
        "n_samples": n,
        "time": t.tolist(),
        "signal": np.asarray(signal_arr, dtype=float).tolist(),
        "reduced": reduced.tolist(),
        "reduced_x": reduced_x,
        "latro": {"lambda": lam, "tau": tau, "rho": rho},
        "latro_windowed": {
            "x": reduced_x,
            "lambda": lambdas_w.tolist(),
            "tau": taus_w.tolist(),
            "rho": rhos_w.tolist(),
        },
        "model_j_points": [int(i) for i in points],
        "model_j_time": [float(t[i]) for i in points],
        "model_j_values": [float(signal_arr[i]) for i in points],
        "window": window,
        "threshold": threshold,
        "drop_last": drop_last,
        "description": description,
    }
    if extra:
        result.update(extra)
    return result


app = FastAPI(title="fusion-tools dashboard")


@app.get("/example")
def example_metadata():
    """Metadane wbudowanego przykladowego sygnalu (patrz data/example_metadata.json)."""
    meta_path = os.path.join(DATA_DIR, "example_metadata.json")
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/analyze")
async def analyze(
    file: Optional[UploadFile] = File(default=None),
    window: int = Form(default=64),
    threshold: float = Form(default=2.0),
    drop_last: bool = Form(default=False),
    use_example: bool = Form(default=False),
    dataset: Optional[str] = Form(default=None),
):
    if use_example or file is None:
        df = pd.read_csv(EXAMPLE_CSV)
        time_arr = df.iloc[:, 0].to_numpy(dtype=float)
        signal_arr = df.iloc[:, 1].to_numpy(dtype=float)
        return _run_pipeline(time_arr, signal_arr, window, threshold, drop_last)

    name = file.filename.lower()
    raw = await file.read()

    if name.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(raw))
        except Exception as e:
            raise HTTPException(400, f"Nie udalo sie odczytac CSV: {e}")
        if df.shape[1] < 2:
            raise HTTPException(400, "CSV musi miec co najmniej dwie kolumny: czas, wartosc.")
        time_arr = df.iloc[:, 0].to_numpy(dtype=float)
        signal_arr = df.iloc[:, 1].to_numpy(dtype=float)
        return _run_pipeline(time_arr, signal_arr, window, threshold, drop_last)

    if name.endswith(".h5") or name.endswith(".hdf5"):
        if load_hdf5 is None:
            raise HTTPException(
                400,
                "Obsluga HDF5 jest niedostepna w tym srodowisku (nie udalo sie "
                f"zaimportowac h5py: {_HDF5_IMPORT_ERROR}). Uzyj pliku .csv, albo "
                "zainstaluj h5py (`pip install h5py`) i uruchom serwer ponownie.",
            )
        try:
            data_dict = load_hdf5(io.BytesIO(raw))
        except Exception as e:
            raise HTTPException(400, f"Nie udalo sie odczytac HDF5: {e}")
        time_arr, signal_arr, info = _select_hdf5_time_signal(data_dict, dataset_param=dataset)
        return _run_pipeline(time_arr, signal_arr, window, threshold, drop_last, extra={"hdf5_info": info})

    raise HTTPException(
        400,
        "Obslugiwane sa tylko pliki .csv (dwie kolumny: czas, wartosc) oraz .h5/.hdf5 "
        "(dowolne 1D numeryczne datasety - patrz pole hdf5_info w odpowiedzi po wgraniu).",
    )


if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def dashboard():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if os.path.isdir(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
