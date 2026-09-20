"""
Kilka nazwanych sygnalow demo dla dashboardu (api.py + static/index.html) i
dla demo/run_demo.py, oprocz pojedynczego wbudowanego przykladu w
data/w7x_mirnov_example.csv.

WSZYSTKIE sygnaly ponizej sa SYNTETYCZNE (deterministycznie generowane z
ustalonym ziarnem RNG) - dokladnie tak samo jak dotychczasowy jedyny
przyklad. Zaden nie pochodzi z prawdziwego urzadzenia fuzyjnego. Nazwy typu
"burst"/"growing_mode" opisuja KSZTALT sygnalu (do celow demonstracyjnych
Modelu J i Lambda-tau-rho), nie twierdza o odwzorowaniu konkretnego
zjawiska plazmowego takiego jak ELM czy sawtooth - patrz README, "Zakres i
ograniczenia".

Kazdy scenariusz ma unikalne id, etykiete/opis po polsku i funkcje
generujaca (time, signal, metadata_dict). "baseline" to ISTNIEJACY
przyklad (czytany z data/w7x_mirnov_example.csv), zeby zachowac dokladnie
ten sam wynik co dotychczasowe testy/demo - pozostale sa generowane on the
fly z ustalonym ziarnem, wiec tez sa w pelni deterministyczne (ten sam
wynik za kazdym uruchomieniem).

Miejsce na PRAWDZIWE dane w przyszlosci: jesli w data/real/ pojawi sie
plik z prawdziwym sygnalem (np. wyciety kanal Mirnova z otwartego zbioru
TCABR, zenodo.org/records/21843354 - patrz README), dodaj go tutaj jako
kolejny wpis w SCENARIOS z source="real:<nazwa zbioru>" zamiast
"synthetic", zeby dashboard i /scenarios jawnie rozroznialy realne dane od
demo - nie mieszaj ich w jednym wpisie.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
BASELINE_CSV = os.path.join(DATA_DIR, "w7x_mirnov_example.csv")
REAL_DATA_DIR = os.path.join(DATA_DIR, "real")
TCABR_METADATA_PATH = os.path.join(REAL_DATA_DIR, "tcabr_samples_metadata.json")


def _baseline():
    df = pd.read_csv(BASELINE_CSV)
    time = df.iloc[:, 0].to_numpy(dtype=float)
    signal = df.iloc[:, 1].to_numpy(dtype=float)
    meta = {
        "source": "synthetic",
        "generation": "suma dwoch sinusoid (3 Hz i 17 Hz) + szum gaussowski (std=0.03) "
                      "+ 3 wstrzykniete gwaltowne 'punkty skretu' w probkach 400, 950, 1600",
        "sampling_rate_hz": 1000,
    }
    return time, signal, meta


def _quiet(n=2000, fs=1000.0, seed=1):
    """Prawie plaski sygnal - tylko drobny szum, ZERO wstrzknietych zdarzen.
    Kontrolka negatywna: Model J powinien wykryc bardzo niewiele albo nic,
    a nie znalezc "zdarzenia" tam, gdzie ich nie wstrzyknieto."""
    rng = np.random.RandomState(seed)
    t = np.arange(n) / fs
    signal = 0.02 * rng.normal(size=n)
    meta = {
        "source": "synthetic",
        "generation": f"czysty szum gaussowski (std=0.02), ZERO wstrzknietych zdarzen "
                       f"(seed={seed}) - kontrolka negatywna",
        "sampling_rate_hz": fs,
    }
    return t, signal, meta


def _single_burst(n=2000, fs=1000.0, seed=2):
    """Cichy sygnal bazowy + jedno wyrazne, izolowane zdarzenie (skok +
    wykladniczy zanik) w polowie sygnalu - jak pojedynczy, silny prekursor
    zaburzenia."""
    rng = np.random.RandomState(seed)
    t = np.arange(n) / fs
    signal = 0.05 * rng.normal(size=n)
    center = n // 2
    tail = np.arange(n - center)
    signal[center:] += 1.5 * np.exp(-tail / 40.0)
    signal[max(0, center - 3):center + 3] += 1.2  # ostry pik na starcie zdarzenia
    meta = {
        "source": "synthetic",
        "generation": f"cichy szum (std=0.05) + 1 wstrzykniete zdarzenie (skok + "
                       f"wykladniczy zanik, stala czasowa 40 probek) w probce {center} "
                       f"(seed={seed})",
        "sampling_rate_hz": fs,
        "injected_events_samples": [center],
    }
    return t, signal, meta


def _growing_mode(n=3000, fs=1000.0, seed=3):
    """Oscylacja o amplitudzie rosnacej wykladniczo przez caly czas trwania
    sygnalu (bez sztucznego wyplaszczenia/nasycenia) - ksztalt czesto
    kojarzony z rosnacym modem MHD przed zdarzeniem, tu wylacznie jako
    ilustracja krzywej narastania energii (rho) w czasie, nie model
    fizyczny. Energia (rho) w drugiej polowie sygnalu jest ~40x wieksza
    niz w pierwszej - patrz test_growing_mode_energy_increases_over_time."""
    rng = np.random.RandomState(seed)
    t = np.arange(n) / fs
    growth_rate = 1.3
    envelope = np.exp(growth_rate * t) * 0.05  # rosnie od 0.05 do ok. 2.5
    signal = envelope * np.sin(2 * np.pi * 12.0 * t) + 0.04 * rng.normal(size=n)
    meta = {
        "source": "synthetic",
        "generation": f"oscylacja 12 Hz z amplituda rosnaca wykladniczo (stala wzrostu="
                       f"{growth_rate}/s, od ok. 0.05 do ok. 2.5) przez caly sygnal, bez "
                       f"nasycenia + szum gaussowski (std=0.04) (seed={seed})",
        "sampling_rate_hz": fs,
    }
    return t, signal, meta


def _noisy_flat(n=2000, fs=1000.0, seed=4):
    """Czysty szum o wiekszej amplitudzie niz 'quiet' - do pokazania, ze
    przy dostatecznie duzym szumie prog statystyczny Modelu J zawsze
    zlapie jakies probki, mimo braku PRAWDZIWEJ struktury w sygnale.
    Ostrzezenie przed nadinterpretacja liczby wykrytych punktow bez
    kontekstu (patrz README, "Zakres i ograniczenia")."""
    rng = np.random.RandomState(seed)
    t = np.arange(n) / fs
    signal = 0.4 * rng.normal(size=n)
    meta = {
        "source": "synthetic",
        "generation": f"czysty szum gaussowski o wiekszej amplitudzie (std=0.4), ZERO "
                       f"prawdziwej struktury (seed={seed}) - pokazuje falszywie dodatnie "
                       f"detekcje Modelu J na samym szumie",
        "sampling_rate_hz": fs,
    }
    return t, signal, meta


SCENARIOS = {
    "baseline": {
        "label": "Bazowy (2 sinusoidy + 3 zdarzenia)",
        "description": "Domyslny przyklad repo: 2 sinusoidy (3 Hz, 17 Hz) + szum + 3 "
                        "wstrzykniete gwaltowne zdarzenia. To ten sam plik co dotychczas "
                        "(data/w7x_mirnov_example.csv).",
        "generator": _baseline,
    },
    "quiet": {
        "label": "Cichy / brak zdarzen (kontrolka negatywna)",
        "description": "Prawie plaski sygnal, sam szum, zero wstrzknietych zdarzen. UWAGA: "
                        "Model J przy domyslnym progu (2.0) i tak wykryje ok. 4-5% probek "
                        "na czystym szumie - to statystyczny efekt progowania z-score, nie "
                        "prawdziwe zdarzenia (patrz 'noisy_flat' i README, 'Zakres i "
                        "ograniczenia'). Ta liczba NIE spada do zera - to zamierzone.",
        "generator": _quiet,
    },
    "single_burst": {
        "label": "Pojedynczy wyrazny wybuch",
        "description": "Cichy sygnal bazowy + jedno silne, izolowane zdarzenie (skok + "
                        "zanik) w polowie sygnalu.",
        "generator": _single_burst,
    },
    "growing_mode": {
        "label": "Rosnacy mod (amplituda wykladnicza)",
        "description": "Oscylacja o amplitudzie rosnacej wykladniczo przez caly sygnal "
                        "(bez nasycenia) - dobry przyklad na wykresie dryfu rho (energia "
                        "rosnie wyraznie w czasie, ~40x wieksza w drugiej polowie).",
        "generator": _growing_mode,
    },
    "noisy_flat": {
        "label": "Sam szum (bez struktury)",
        "description": "Czysty, silniejszy szum bez zadnej prawdziwej struktury - "
                        "pokazuje falszywie dodatnie detekcje Modelu J na samym szumie.",
        "generator": _noisy_flat,
    },
}


def _make_real_csv_generator(csv_path, extra_meta):
    """Buduje funkcje generujaca dla jednego realnego pliku CSV (2 kolumny:
    time,signal - ten sam format co reszta repo). `extra_meta` to dict z
    prawdziwa proweniencja (patrz _load_real_tcabr_scenarios) dolaczany do
    wyniku bez zmian."""

    def _generator():
        df = pd.read_csv(csv_path)
        time = df.iloc[:, 0].to_numpy(dtype=float)
        signal = df.iloc[:, 1].to_numpy(dtype=float)
        return time, signal, dict(extra_meta)

    return _generator


def _load_real_tcabr_scenarios():
    """
    Wczytuje realne (NIE syntetyczne) sygnaly TCABR z data/real/, jesli
    tam sa (patrz data/real/README.md i extract_tcabr_samples.py) -
    zamienia data/real/tcabr_samples_metadata.json + towarzyszace CSV na
    wpisy SCENARIOS, source="real:tcabr" (odroznione od "synthetic" -
    patrz docstring modulu). Zwraca pusty dict, jesli plik metadanych nie
    istnieje (normalne - repo dziala bez realnych danych, patrz reszta
    tego pliku) - blad parsowania jest LOGOWANY, nie wywala calej
    aplikacji, bo brak/blad w opcjonalnych realnych danych nie powinien
    psuc syntetycznych demo.
    """
    if not os.path.isfile(TCABR_METADATA_PATH):
        return {}

    try:
        with open(TCABR_METADATA_PATH, encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as exc:  # noqa: BLE001 - opcjonalne dane, nie wywalaj apki
        print(f"UWAGA: nie udalo sie wczytac {TCABR_METADATA_PATH}: {exc}")
        return {}

    scenarios = {}
    for sample in meta.get("samples", []):
        shot_id = sample["shot_id"]
        disruptive = sample["disruptive"]
        dtime = sample.get("disruption_time_s")
        dmethod = sample.get("disruption_time_method")
        status_pl = "zaklocajacy (disruptive)" if disruptive else "normalny (non-disruptive)"

        for ch in sample.get("channels", []):
            channel = ch["channel"]
            csv_path = os.path.join(REAL_DATA_DIR, ch["file"])
            if not os.path.isfile(csv_path):
                print(f"UWAGA: brakuje pliku {csv_path} z metadanych TCABR - pomijam.")
                continue

            sid = f"tcabr_{shot_id}_{channel}"
            if dtime is not None:
                event_txt = f"Realny czas zaklocenia: {dtime:.4f} s ({dmethod})."
            else:
                event_txt = "Strzal normalny - brak zaklocenia."
            validation_note = sample.get("model_j_validation_note", "")
            description = (
                f"PRAWDZIWY sygnal {channel} z tokamaka TCABR, strzal {shot_id} "
                f"({status_pl}). {event_txt} Zrodlo: {sample.get('source', 'TCABR/Zenodo')}."
                + (f" {validation_note}" if validation_note else "")
            )
            extra_meta = {
                "source": f"real:tcabr:shot_{shot_id}",
                "generation": description,
                "shot_id": shot_id,
                "channel": channel,
                "disruptive": disruptive,
                "disruption_time_s": dtime,
                "disruption_time_method": dmethod,
                "model_j_validation_note": validation_note,
            }
            scenarios[sid] = {
                "label": f"TCABR #{shot_id} {channel} ({'zaklocajacy' if disruptive else 'normalny'})",
                "description": description,
                "generator": _make_real_csv_generator(csv_path, extra_meta),
            }
    return scenarios


# Doklejamy realne scenariusze TCABR (jesli sa) NA KONCU, po syntetycznych
# - kolejnosc w SCENARIOS = kolejnosc w selektorze dashboardu, wiec
# syntetyczne demo zostaja pierwsze/domyslne, realne dane sa dodatkiem.
SCENARIOS.update(_load_real_tcabr_scenarios())


def list_scenarios():
    """Zwraca liste {id, label, description} dla wszystkich scenariuszy -
    do endpointu GET /scenarios (bez generowania sygnalow, tanie)."""
    return [
        {"id": sid, "label": s["label"], "description": s["description"]}
        for sid, s in SCENARIOS.items()
    ]


def generate_scenario(scenario_id):
    """Generuje (time, signal, metadata) dla danego id. Rzuca KeyError,
    jesli id nie istnieje (api.py tlumaczy to na HTTP 400)."""
    if scenario_id not in SCENARIOS:
        raise KeyError(scenario_id)
    entry = SCENARIOS[scenario_id]
    time, signal, meta = entry["generator"]()
    meta = dict(meta)
    meta["id"] = scenario_id
    meta["label"] = entry["label"]
    meta["n_samples"] = len(signal)
    return np.asarray(time, dtype=float), np.asarray(signal, dtype=float), meta
