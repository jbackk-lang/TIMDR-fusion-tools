import numpy as np


def latro(signal):
    """
    Lambda-tau-rho (Λ-τ-ρ): podstawowe metryki strukturalne sygnalu.

    Definicje (zgodne z opisem w README, ktory je podaje wprost):
      Lambda (lam) - amplituda zakresu sygnalu:      max(signal) - min(signal)
      tau           - srednia wartosc bezwzgledna:    mean(|signal|)
      rho           - energia sygnalu (srednia moc):  mean(signal**2)

    To jest CELOWO jedyna definicja w tym repozytorium. Wczesniej istnialy
    trzy rozne, wzajemnie niespojne wersje "Λ-τ-ρ": ta funkcja (inna,
    oparta na gradiencie), latro_features() (jeszcze inna: tau=std(signal))
    i przyklad w README (ta wersja ponizej). Skonsolidowano je do jednej,
    zeby nazwa "Λ-τ-ρ" znaczyla to samo wszedzie w repo.
    latro_features() jest teraz cienkim wrapperem nad ta funkcja.

    Parametry:
      signal - sekwencja liczb (lista / np.ndarray), niepusta.

    Zwraca:
      (lam, tau, rho) jako float.

    Rzuca:
      ValueError, jesli signal jest pusty.
    """
    x = np.asarray(signal, dtype=float)
    if x.size == 0:
        raise ValueError("latro(): signal jest pusty")
    lam = float(np.max(x) - np.min(x))
    tau = float(np.mean(np.abs(x)))
    rho = float(np.mean(x ** 2))
    return lam, tau, rho


def latro_windowed(signal, window=64, drop_last=False):
    """
    latro() liczony osobno dla kazdego kolejnego okna sygnalu, zamiast
    jednej sumarycznej trojki (Λ, τ, ρ) na caly sygnal. Pozwala zobaczyc
    JAK Λ-τ-ρ zmieniaja sie w czasie (np. skok energii przy zdarzeniu),
    a nie tylko ich usrednioną wartosc.

    Uzywa dokladnie tego samego podzialu na okna co timdr() (ten sam
    parametr `window`, to samo zachowanie ostatniego niepelnego okna
    przez `drop_last`), zeby wyniki byly wyrownane z ta sama osia X
    (np. reduced_x z timdr()).

    Parametry:
      signal    - sekwencja liczb.
      window    - rozmiar okna w probkach (domyslnie 64).
      drop_last - patrz timdr() (domyslnie False).

    Zwraca:
      (lambdas, taus, rhos) jako trzy np.ndarray, po jednej wartosci na
      okno. Pusta trojka tablic, jesli signal jest pusty.
    """
    x = np.asarray(signal, dtype=float)
    lambdas, taus, rhos = [], [], []
    for i in range(0, len(x), window):
        chunk = x[i:i + window]
        if len(chunk) == 0:
            break
        if len(chunk) < window and drop_last:
            break
        lam, tau, rho = latro(chunk)
        lambdas.append(lam)
        taus.append(tau)
        rhos.append(rho)
    return np.array(lambdas), np.array(taus), np.array(rhos)
