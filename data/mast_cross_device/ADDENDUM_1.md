# ADDENDUM 1 do PREREGISTRATION.md (zapisany PRZED pierwszym uruchomieniem detektorow na MAST)

Kontrola jakosci danych (bez uzycia wynikow detektorow), sample: 579 strzalow (shot_list_frozen.txt), magnetics/ip + magnetics/time:
- 0 bledow dekodowania, n == nt dla kazdego strzalu, brak brakujacych chunkow, brak NaN.
- dt = 0,2 ms jednorodne we wszystkich strzalach (max wzgledne odchylenie 0), jednostka A, tstart = -0,1 s, czas trwania 0,27-2,38 s.
- 18 strzalow ma odwrocona konwencje znaku pradu (|min| > |max|): 13493, 13516, 13536, 13559, 13585, 13625, 13654, 13680, 22394, 22423, 22443, 22474, 22494, 22520, 22544, 22564, 22587, 22610.
- Brak strzalow bez plazmy: najmniejsza wartosc max(|Ip|) po uwzglednieniu konwencji znaku wynosi 0,28 MA (strzal 19301).

Regula QC R1 (zamrozona): jesli |min(ip)| > |max(ip)|, ip := -ip (tylko konwencja znaku; detektory zakladaja dodatni prad). Regula wynika ze statystyk QC, nie z wynikow detektorow.
Brak innych wykluczen: wszystkie 579 strzalow wchodza do analizy.

Kod pod testem: TIMDR-fusion-tools/model_j/model_j_detector.py, sha256 908ee2f2855c9bffde050f737bc398aaa30f9e1164b2c50c42ed0dc2c5c11734 (bez modyfikacji).
Skrypt uruchomieniowy: run_mast_frozen.py (sha256 w PREREGISTRATION_HASHES.txt). Uruchomienie: jedno, po zapisie hashy.
