from latro.latro_core import latro


def latro_features(signal):
    """
    Ekstrahuje cechy Lambda-tau-rho (Λ-τ-ρ) dla sygnalu jako slownik.

    Cienki wrapper nad latro_core.latro() - jedyne miejsce, gdzie te
    wartosci sa faktycznie liczone. Wczesniej ta funkcja liczyla tau i rho
    inaczej niz latro_core.latro() (tau=std(signal) zamiast mean(|signal|)),
    co dawalo dwie rozne liczby pod tymi samymi nazwami w tym samym repo.

    Zwraca:
      dict z kluczami "lambda", "tau", "rho".
    """
    lam, tau, rho = latro(signal)
    return {"lambda": lam, "tau": tau, "rho": rho}
