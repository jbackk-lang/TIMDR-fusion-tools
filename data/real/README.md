# Prawdziwe dane (miejsce docelowe)

Ten katalog jest miejscem na PRAWDZIWE (nie syntetyczne) sygnaly do
`TIMDR-fusion-tools` - w odroznieniu od `data/w7x_mirnov_example.csv`,
ktory jest syntetyczny (patrz `data/example_metadata.json`).

## TCABR (Zenodo, DOI 10.5281/zenodo.21843354)

Realny, wolno dostepny zbior: 2189 wyladowan z tokamaka TCABR
(Universidade de Sao Paulo), CC-BY 4.0, prawdziwe cewki Mirnova
(20 na strzal), rozdzielczosc 1 mikrosekunda, 435 z nich disruptive.
https://zenodo.org/records/21843354

Plik danych (`tcabr_data.nc`) ma 4.8 GB - za duzy, zeby przeslac go do
sandboxa, w ktorym powstal ten kod (network allowlist go blokuje, a i tak
byloby to za duzo danych na transfer przez ten kanal). Dlatego:

1. **Ty** pobierasz `tcabr_data.nc` (i opcjonalnie dolaczony
   `tcabr_tools.py`) bezposrednio z Zenodo na swoim komputerze.
2. Uruchamiasz `extract_tcabr_samples.py` (w tym katalogu) **u siebie**:

   ```bash
   pip install xarray netCDF4 numpy pandas
   python extract_tcabr_samples.py --nc /sciezka/do/tcabr_data.nc --inspect-only
   ```

   `--inspect-only` tylko wypisuje prawdziwa strukture pliku (grupy/
   zmienne/atrybuty) - **zrob to najpierw**, zeby sprawdzic, czy nazwy
   zmiennych (`BbMirnovN01`...`BbMirnovN20`, `time` itd.) faktycznie
   zgadzaja sie z tym, co skrypt zaklada na podstawie opisu datasetu na
   Zenodo (skrypt zostal napisany bez dostepu do prawdziwego pliku).

3. Jesli struktura sie zgadza, uruchamiasz bez `--inspect-only`, zeby
   faktycznie wyciac co najmniej 3 probki jako CSV:

   ```bash
   python extract_tcabr_samples.py --nc /sciezka/do/tcabr_data.nc --n-samples 3
   ```

   To zapisze pliki `tcabr_shot_<id>_<kanal>.csv` (format `time,signal`,
   zgodny z `parsers/csv_parser.py`) plus `tcabr_samples_metadata.json` z
   prawdziwa proweniencja (shot ID, kanal, czy strzal byl disruptive,
   zrodlo/DOI).

4. Wgraj wynikowe CSV do dashboardu (`http://127.0.0.1:8000/`, pole "Plik
   CSV lub HDF5") - albo daj znac, zeby dodac je jako oddzielny scenariusz
   `source="real:tcabr"` w `demo/scenarios.py` (kod ma juz przygotowane na
   to miejsce - patrz komentarz na gorze tego pliku), obok istniejacych
   syntetycznych.

Jesli struktura pliku okaze sie inna niz zaklada skrypt (np. inne nazwy
zmiennych, brak grup), `--inspect-only` powie dokladnie co jest w pliku
naprawde - podesla mi ten wydruk, a dostosuje skrypt do prawdziwej
struktury zamiast zgadywac dalej.
