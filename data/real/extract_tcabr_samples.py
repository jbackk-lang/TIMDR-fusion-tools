"""
Wycina co najmniej 3 realne probki (Mirnov + czas) z prawdziwego zbioru
TCABR (Tokamak a Chauffage Alfven Bresilien, Uniwersytet Sao Paulo) do
formatu CSV, ktorego oczekuje TIMDR-fusion-tools (2 kolumny: time, signal
- patrz parsers/csv_parser.py).

Zrodlo danych (prawdziwe, NIE syntetyczne): "Experimental Plasma Discharge
Dataset from the TCABR Tokamak", Zenodo, DOI 10.5281/zenodo.21843354,
CC-BY 4.0, 2189 realnych wyladowan (1754 nie-disruptive + 435 disruptive),
20 prawdziwych cewek Mirnova na wyladowanie, rozdzielczosc 1 mikrosekunda.
https://zenodo.org/records/21843354

WYMAGA URUCHOMIENIA NA TWOIM KOMPUTERZE, NIE W SANDBOXIE:
    Plik danych (tcabr_data.nc, 4.8 GB) jest za duzy zeby przeslac go
    do/z tego srodowiska (sandbox blokuje zenodo.org, a nawet gdyby nie
    blokowal, 4.8 GB to za duzo na transfer przez ten kanal). Ten skrypt
    zostal napisany BEZ dostepu do prawdziwego pliku - jest defensywny:
    najpierw wypisuje faktyczna strukture pliku (grupy/zmienne), zeby
    dalo sie zweryfikowac zalozenia ponizej PRZED zapisaniem czegokolwiek,
    zamiast zgadywac po cichu.

Instalacja (na Twoim komputerze):
    pip install xarray netCDF4 numpy pandas

Uzycie:
    python extract_tcabr_samples.py --nc /sciezka/do/tcabr_data.nc
    python extract_tcabr_samples.py --nc tcabr_data.nc --n-samples 5 --mirnov-channel BbMirnovN03
    python extract_tcabr_samples.py --nc tcabr_data.nc --inspect-only

Co robi:
    1. Otwiera plik przez netCDF4 (obsluguje hierarchiczne grupy po shot
       ID - xarray.open_dataset() sam z siebie NIE wchodzi w grupy).
    2. Wypisuje pierwsze kilka grup i ich zmienne/atrybuty - zeby moc
       zweryfikowac, ze nazwy ponizej (BbMirnovN01 itd., zgodnie z opisem
       datasetu na Zenodo) faktycznie sie zgadzaja z prawdziwym plikiem.
    3. Probuje wykryc etykiete disruptive/non-disruptive per shot (kilka
       typowych nazw atrybutu/zmiennej - patrz DISRUPTIVE_FLAG_CANDIDATES).
       Jesli sie nie uda automatycznie, jawnie to mowi zamiast zgadywac.
    4. Wybiera co najmniej `--n-samples` strzalow (domyslnie 3), starajac
       sie wziac MIX disruptive/non-disruptive jesli etykieta jest znana
       (bo to ciekawszy test niz same podobne przypadki), inaczej po
       prostu pierwsze N.
    5. Dla kazdego wybranego strzalu: wyciaga jeden kanal Mirnova (patrz
       --mirnov-channel) + JEGO WLASNA os czasu (KAZDY kanal w TCABR ma
       osobna os czasu - potwierdzone i uwzglednione tez przez
       tcabr_tools.py, wiec NIE zaklada sie jednej wspolnej zmiennej
       "time" per grupa/strzal - patrz _find_channel_time() nizej),
       zapisuje jako data/real/tcabr_shot_<id>_<channel>.csv
       (naglowek: time,signal) - oraz zbiorczy
       data/real/tcabr_samples_metadata.json z prawdziwa proweniencja
       (shot id, kanal, jak znaleziono os czasu, etykieta jesli znana,
       zrodlo/DOI).

Po wygenerowaniu plikow: dodaj je jako scenariusz(e) w
demo/scenarios.py z source="real:tcabr" (patrz komentarz w tym pliku),
zamiast mieszac je z syntetycznymi.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

DOI = "10.5281/zenodo.21843354"
SOURCE_URL = "https://zenodo.org/records/21843354"

# Nazwy zmiennych zgodnie z opisem datasetu na Zenodo (tabela "Diagnostic
# Alias") - do weryfikacji przy pierwszym uruchomieniu przez --inspect-only.
MIRNOV_CHANNELS = [f"BbMirnovN{i:02d}" for i in range(1, 21)]

# KAZDY kanal w TCABR ma WLASNA, osobna os czasu (potwierdzone; tak samo
# zaklada dolaczone do datasetu tcabr_tools.py) - NIE ma jednej wspolnej
# zmiennej "time" per grupa/strzal, ktorej mozna by uzyc dla dowolnego
# kanalu. _find_channel_time() nizej szuka osi czasu SPECYFICZNEJ dla
# danego kanalu, w tej kolejnosci:
#   1. standardowa konwencja NetCDF/CF: zmienna wspoldzielaca nazwe z
#      wymiarem (dimension) danego kanalu jest jego zmienna wspolrzednych
#      (coordinate variable) - to najbardziej wiarygodne zrodlo, bo nie
#      zaleza od konkretnej konwencji nazewnictwa tego datasetu.
#   2. atrybut "coordinates" na zmiennej kanalu (konwencja CF) - jesli
#      wskazuje na zmienna czasu, uzyj jej.
#   3. nazwy odgadywane z nazwy kanalu (np. "BbMirnovN01_time",
#      "time_BbMirnovN01", "BbMirnovN01Time") - fallback, jesli 1-2 zawioda.
CHANNEL_TIME_NAME_PATTERNS = [
    "{ch}_time", "{ch}Time", "time_{ch}", "t_{ch}", "{ch}_t",
]
# Ostateczny fallback: wspolna zmienna czasu per grupa (na wypadek, gdyby
# jednak niektore kanaly ja mialy, mimo ogolnej zasady powyzej).
SHARED_TIME_CANDIDATES = ["time", "t", "Time", "TIME"]

DISRUPTIVE_FLAG_CANDIDATES = [
    "disruptive", "is_disruptive", "disruption", "disrupted", "label", "class",
]


def _open_root(nc_path):
    import netCDF4  # noqa: import here so --help works without the dependency installed

    return netCDF4.Dataset(nc_path, "r")


def inspect(nc_path, max_groups=5):
    root = _open_root(nc_path)
    try:
        print(f"Top-level dims: {list(root.dimensions.keys())}")
        print(f"Top-level vars: {list(root.variables.keys())}")
        print(f"Top-level attrs: {dict(root.__dict__)}")
        group_names = list(root.groups.keys())
        print(f"\nLiczba grup (prawdopodobnie = liczba strzalow): {len(group_names)}")
        for name in group_names[:max_groups]:
            g = root.groups[name]
            print(f"\n--- grupa '{name}' ---")
            print(f"  vars: {list(g.variables.keys())}")
            print(f"  attrs: {dict(g.__dict__)}")
        return group_names
    finally:
        root.close()


def _find_disruptive_flag(group):
    for cand in DISRUPTIVE_FLAG_CANDIDATES:
        if cand in group.__dict__:
            return bool(group.__dict__[cand])
        if cand in group.variables:
            try:
                val = group.variables[cand][...]
                return bool(val)
            except Exception:
                pass
    return None


def _find_var(group, candidates):
    for cand in candidates:
        if cand in group.variables:
            return cand
    return None


def _find_channel_time(group, channel):
    """
    Znajduje os czasu SPECYFICZNA dla danego kanalu (potwierdzone: w TCABR
    kazdy kanal ma wlasna, osobna os czasu - tak samo zaklada tcabr_tools.py
    - patrz komentarz przy CHANNEL_TIME_NAME_PATTERNS na gorze pliku).
    Zwraca (nazwa_zmiennej_lub_None, "jak_znaleziono").
    """
    var = group.variables[channel]

    # 1. konwencja NetCDF/CF: zmienna wspoldzielaca nazwe z wymiarem tego
    #    kanalu jest jego zmienna wspolrzednych - najbardziej wiarygodne,
    #    bo nie zalezy od konwencji nazewnictwa TEGO konkretnego datasetu.
    for dim_name in var.dimensions:
        if dim_name in group.variables and dim_name != channel:
            return dim_name, f"coordinate-variable-for-dim:{dim_name}"

    # 2. atrybut "coordinates" (konwencja CF)
    coords_attr = getattr(var, "coordinates", None)
    if coords_attr:
        for cand in str(coords_attr).split():
            if cand in group.variables and cand != channel:
                return cand, f"coordinates-attr:{cand}"

    # 3. nazwy odgadywane z nazwy kanalu
    for pattern in CHANNEL_TIME_NAME_PATTERNS:
        cand = pattern.format(ch=channel)
        if cand in group.variables:
            return cand, f"name-pattern:{cand}"

    # 4. ostateczny fallback: wspolna zmienna czasu per grupa (na wypadek
    #    gdyby TEN kanal jednak ja mial, mimo ze regula ogolna mowi, ze
    #    kazdy kanal ma wlasna)
    shared = _find_var(group, SHARED_TIME_CANDIDATES)
    if shared is not None:
        return shared, f"shared-fallback:{shared}"

    return None, None


def select_shots(root, n_samples):
    group_names = list(root.groups.keys())
    if not group_names:
        raise RuntimeError(
            "Plik nie ma grup (root.groups jest puste) - struktura pliku "
            "jest inna niz zakladalismy. Uruchom --inspect-only i sprawdz "
            "root.variables/root.dimensions zamiast root.groups."
        )

    labeled = []
    unlabeled = []
    for name in group_names:
        g = root.groups[name]
        flag = _find_disruptive_flag(g)
        if flag is None:
            unlabeled.append(name)
        else:
            labeled.append((name, flag))

    chosen = []
    if labeled:
        disruptive = [n for n, f in labeled if f]
        non_disruptive = [n for n, f in labeled if not f]
        print(
            f"Wykryto etykiete disruptive/non-disruptive dla {len(labeled)}/"
            f"{len(group_names)} grup ({len(disruptive)} disruptive, "
            f"{len(non_disruptive)} non-disruptive)."
        )
        # mix: try to alternate disruptive/non-disruptive for variety
        i = j = 0
        while len(chosen) < n_samples and (i < len(disruptive) or j < len(non_disruptive)):
            if i < len(disruptive):
                chosen.append((disruptive[i], True))
                i += 1
            if len(chosen) < n_samples and j < len(non_disruptive):
                chosen.append((non_disruptive[j], False))
                j += 1
    else:
        print(
            "UWAGA: nie udalo sie automatycznie wykryc etykiety disruptive/"
            "non-disruptive (sprawdzone kandydaci: "
            f"{DISRUPTIVE_FLAG_CANDIDATES}). Biore po prostu pierwsze "
            "N grup - sprawdz strukture przez --inspect-only, jesli "
            "etykieta jest Ci potrzebna, i dopisz jej prawdziwa nazwe do "
            "DISRUPTIVE_FLAG_CANDIDATES na gorze tego pliku."
        )
        for name in group_names[:n_samples]:
            chosen.append((name, None))

    if len(chosen) < n_samples:
        for name in group_names:
            if len(chosen) >= n_samples:
                break
            if name not in [c[0] for c in chosen]:
                chosen.append((name, None))

    return chosen[:n_samples]


def extract_shot(root, shot_id, mirnov_channel, out_dir):
    import numpy as np

    g = root.groups[shot_id]

    channel = mirnov_channel or _find_var(g, MIRNOV_CHANNELS)
    if channel is None or channel not in g.variables:
        raise RuntimeError(
            f"Shot '{shot_id}': kanal '{mirnov_channel}' nie istnieje. "
            f"Dostepne zmienne w tej grupie: {list(g.variables.keys())}"
        )
    signal = np.asarray(g.variables[channel][...], dtype=float)

    time_name, how_found = _find_channel_time(g, channel)
    if time_name is not None:
        time = np.asarray(g.variables[time_name][...], dtype=float)
        time_source = f"dataset:{time_name} ({how_found})"
    else:
        # brak jawnej osi czasu dla TEGO kanalu - uzyj indeksow probek,
        # jawnie to oznacz (dokladnie ten sam wzorzec co
        # parsers/hdf5_parser.py + _select_hdf5_time_signal() w api.py dla
        # wgrywanych plikow HDF5 bez datasetu czasu)
        time = np.arange(len(signal), dtype=float)
        time_source = "synthetic_index (brak osi czasu dla tego kanalu)"
        print(f"  UWAGA shot {shot_id}/{channel}: {time_source}")

    if len(time) != len(signal):
        raise RuntimeError(
            f"Shot '{shot_id}': dlugosc czasu ({len(time)}) != dlugosc "
            f"sygnalu ({len(signal)}) - sprawdz recznie ta grupe."
        )

    fname = f"tcabr_shot_{shot_id}_{channel}.csv"
    fpath = os.path.join(out_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("time,signal\n")
        for t, s in zip(time, signal):
            f.write(f"{t},{s}\n")

    return {
        "file": fname,
        "shot_id": str(shot_id),
        "channel": channel,
        "n_samples": int(len(signal)),
        "time_source": time_source,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nc", required=True, help="sciezka do tcabr_data.nc")
    ap.add_argument("--n-samples", type=int, default=3, help="ile strzalow wyciac (domyslnie 3)")
    ap.add_argument("--mirnov-channel", default=None, help="wymus konkretny kanal (domyslnie: pierwszy dostepny BbMirnovNxx)")
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)), help="katalog docelowy (domyslnie: obok tego skryptu, czyli data/real/)")
    ap.add_argument("--inspect-only", action="store_true", help="tylko wypisz strukture pliku, nic nie zapisuj")
    args = ap.parse_args()

    if not os.path.isfile(args.nc):
        print(f"Nie znaleziono pliku: {args.nc}", file=sys.stderr)
        sys.exit(1)

    if args.inspect_only:
        inspect(args.nc)
        return

    root = _open_root(args.nc)
    try:
        chosen = select_shots(root, args.n_samples)
        print(f"\nWybrane strzaly: {chosen}\n")

        results = []
        for shot_id, disruptive_flag in chosen:
            print(f"Wycinam shot {shot_id} (disruptive={disruptive_flag})...")
            meta = extract_shot(root, shot_id, args.mirnov_channel, args.out_dir)
            meta["disruptive"] = disruptive_flag
            results.append(meta)
            print(f"  -> {meta['file']} ({meta['n_samples']} probek)")
    finally:
        root.close()

    metadata = {
        "source": f"real:tcabr ({SOURCE_URL}, DOI {DOI}, CC-BY 4.0)",
        "note": "Prawdziwe dane z tokamaka TCABR (Universidade de Sao Paulo) - "
                "NIE syntetyczne. disruptive=null oznacza, ze etykiety nie "
                "udalo sie automatycznie wykryc - sprawdz recznie.",
        "samples": results,
    }
    meta_path = os.path.join(args.out_dir, "tcabr_samples_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"\nZapisano metadane: {meta_path}")
    print(f"Zapisano {len(results)} plikow CSV w {args.out_dir}")


if __name__ == "__main__":
    main()
