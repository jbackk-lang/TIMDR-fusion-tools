@echo off
REM run.bat - uruchamia dashboard fusion-tools lokalnie na Windows.
REM
REM Co robi:
REM   1. Tworzy lokalne srodowisko wirtualne .venv (jesli jeszcze nie istnieje).
REM   2. Instaluje/aktualizuje zaleznosci z requirements.txt.
REM   3. Sprawdza, czy port 8000 nie jest juz zajety (patrz uwaga nizej).
REM   4. Otwiera dashboard w domyslnej przegladarce.
REM   5. Startuje serwer API (uvicorn) na http://127.0.0.1:8000
REM      - dashboard: http://127.0.0.1:8000/
REM      - dokumentacja Swagger: http://127.0.0.1:8000/docs
REM
REM Wymaga Pythona 3.8+ dostepnego w PATH jako "python".
REM Zatrzymanie serwera: Ctrl+C w tym oknie (zamkniecie okna "krzyzykiem"
REM  zamiast Ctrl+C moze czasem zostawic proces dzialajacy w tle i
REM  blokujacy port 8000 przy kolejnym uruchomieniu - patrz krok 3 wyzej).

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [BLAD] Nie znaleziono "python" w PATH. Zainstaluj Pythona 3.8+ z python.org
    echo        i zaznacz "Add python.exe to PATH" podczas instalacji.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Tworze srodowisko wirtualne .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [BLAD] Nie udalo sie utworzyc .venv
        pause
        exit /b 1
    )
) else (
    echo [1/5] .venv juz istnieje, pomijam tworzenie.
)

echo [2/5] Instaluje zaleznosci z requirements.txt ...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [BLAD] Instalacja zaleznosci nie powiodla sie.
    pause
    exit /b 1
)

REM Jesli poprzednie uruchomienie zakonczylo sie awaryjnie (np. zamkniecie
REM okna konsoli krzyzykiem zamiast Ctrl+C), python.exe czasem zostaje
REM "zombie" i nadal trzyma port 8000. Wtedy TEN start natychmiast wywala
REM sie bledem "address already in use" - a to wyglada dokladnie tak samo
REM jak "serwer sie wylaczyl" (przegladarka pokazuje pusta/martwa strone),
REM mimo ze nowy serwer tak naprawde nigdy nie wstal. Sprawdzamy to z
REM wyprzedzeniem, zeby dac jasny komunikat zamiast tajemniczej ciszy.
echo [3/5] Sprawdzam czy port 8000 jest wolny ...
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>nul
if not errorlevel 1 (
    echo [UWAGA] Port 8000 jest juz zajety - prawdopodobnie przez proces z
    echo         poprzedniego, nie do konca zamknietego uruchomienia.
    echo         Otworz Menedzer zadan, znajdz "python.exe" ^(albo "pythonw.exe"^)
    echo         i zakoncz go, po czym uruchom run.bat ponownie. Mozesz tez
    echo         sprawdzic ktory proces trzyma port komenda:
    echo             netstat -ano ^| findstr :8000
    echo         i zakonczyc go recznie: taskkill /PID ^<numer^> /F
    pause
    exit /b 1
)

echo [4/5] Otwieram dashboard w przegladarce (za 2 sekundy) ...
start "" cmd /c "timeout /t 2 >nul & start http://127.0.0.1:8000/"

echo [5/5] Startuje API na http://127.0.0.1:8000  (dashboard: /, dokumentacja: /docs)
echo        Zatrzymanie: Ctrl+C
".venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
set UVICORN_EXIT=%errorlevel%

REM Jesli serwer wywali sie od razu po starcie (np. bledna wersja Pythona,
REM brakujaca zaleznosc), to okno konsoli - odpalone dwuklikiem, nie z
REM istniejacego juz terminala - normalnie znika natychmiast, zanim zdazysz
REM przeczytac blad ("miga i gasnie"). Ten "pause" zatrzymuje okno zawsze,
REM tak zeby traceback powyzej byl widoczny (Ctrl+C tez konczy tu z bledem
REM roznym od 0 w cmd, wiec pause jest bezwarunkowy, nie tylko na blad).
echo.
if not "%UVICORN_EXIT%"=="0" (
    echo [BLAD] Serwer zakonczyl sie z kodem %UVICORN_EXIT% - patrz traceback powyzej.
) else (
    echo Serwer zatrzymany.
)
pause

endlocal
