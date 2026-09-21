# Analiza eksploracyjna POST HOC (po odmrozeniu) - NIE zmienia werdyktu pre-rejestracji

Werdykt pre-rejestrowany pozostaje: K2 spelnione, K1 niespelnione (11,1% w oknie 7,5-30 ms, prog 10%), K3 bez zwiazku.
Ponizsze wnioski sa post hoc i wymagaja niezaleznego potwierdzenia (etykiety / nowa probka).

1. Kontrola rozdzielczosci (TCABR, 19 z 20 plikow; plik 15_disruptive_shot_17719.npz jest uciety u zrodla):
   po zejsciu do kroku 0,2 ms i z zamrozonymi parametrami MAST is_fast_quench nadal rozdziela klasy 14/14 i 5/5
   (zaniki 0,6-3,5 ms vs 27-37 ms). Rozdzielczosc sama nie tlumaczy klastra 2-3 ms na MAST.
   Uwaga: pierwsza wersja kontroli miala moj blad (regula znaku R1 uzyta na sygnale z artefaktem digitizera +-152 na starcie
   odwrocila znak); poprawiona bez korekty znaku. Regula R1 na MAST jest odporna (ten sam zbior 18 strzalow po ograniczeniu do x[40:]).
2. MAST: rozklad log10(czas zaniku) jest silnie dwumodalny (BIC: k=1 1285, k=2 882, k=3 698); skladniki 2,2 ms (62%) i 52 ms (38%),
   granica 50/50 przy 7,7 ms. Przerwa to ok. 4-15 ms (~29 strzalow, 5%); dolna czesc wolnego trybu (15-30 ms, 50 strzalow) lezy tuz nad progiem 15 ms.
3. K1 byl skonstruowany zle: okno [7,5; 30] ms obejmuje dolna polowe trybu wolnego (czesciowo tez normalne strzaly TCABR, 19-38 ms wg README repo), wiec nie mierzy przerwy.
