"""
Dzialajacy, w pelni offline demo pipeline'u fusion-tools.

Uzywa PRAWDZIWYCH funkcji bibliotecznych (nie reimplementacji z README) na
syntetycznym przykladowym sygnale w data/w7x_mirnov_example.csv (patrz
data/example_metadata.json - to NIE sa prawdziwe dane z W7-X).

Uruchomienie (z katalogu glownego repo):
    pip install -r requirements.txt
    python demo/run_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.csv_parser import load_csv
from timdr.timdr_filter import timdr
from timdr.timdr_visualization import plot_timdr
from latro.latro_core import latro, latro_windowed
from model_j.model_j_detector import model_j


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(repo_root, "data", "w7x_mirnov_example.csv")

    time, signal = load_csv(csv_path)
    print(f"Wczytano sygnal: {len(signal)} probek")

    window = 64
    reduced = timdr(signal, window=window)
    print(f"TIMDR: zredukowano do {len(reduced)} probek (window={window})")

    lam, tau, rho = latro(signal)
    print(f"Lambda-tau-rho (caly sygnal): lambda={lam:.4f}, tau={tau:.4f}, rho={rho:.4f}")

    lambdas_w, taus_w, rhos_w = latro_windowed(signal, window=window)
    print(f"Lambda-tau-rho per okno: {len(rhos_w)} okien, rho w zakresie [{rhos_w.min():.4f}, {rhos_w.max():.4f}]")

    points = model_j(signal, threshold=2.0)
    print(f"Model J: wykryto {len(points)} punktow skretu: {list(points)[:20]}")

    try:
        plot_timdr(signal, reduced, window=window, time=time)
    except Exception as e:
        # w srodowisku bez ekranu (np. CI, sandbox) plt.show() moze nie
        # dzialac - to nie jest blad demo, tylko brak GUI.
        print(f"(pomijam wyswietlenie wykresu: {e})")


if __name__ == "__main__":
    main()
