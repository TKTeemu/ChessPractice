@echo off
rem Installs the Python packages Chessboard needs (Pillow) into Python 3.15.
rem Uses the wheels folder if there is one (no network needed), otherwise PyPI.
cd /d "%~dp0"
set PY=py -3.15
%PY% -c "" >nul 2>nul || set PY=python
if exist wheels\ (
    %PY% -m pip install --no-index --find-links wheels -r requirements-global.txt
) else (
    %PY% -m pip install -r requirements-global.txt
)
if errorlevel 1 (
    echo.
    echo Installation failed. See the messages above.
    pause
    exit /b 1
)
echo.
echo Done. Start Chessboard with Shakkilauta.bat.
pause
