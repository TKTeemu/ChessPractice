@echo off
rem Sets up Chessboard after unpacking. Safe to run again: it only does what is still missing.
rem   1. checks that Python 3.15 is installed (opens its download if not)
rem   2. installs Pillow into Python, from the wheels folder if there is one, otherwise from PyPI
rem   3. installs python-chess into the vendor folder, unless it is already there
rem   4. puts Stockfish at engines\stockfish\stockfish.exe: fixes a wrong name or subfolder,
rem      otherwise downloads the release below and checks its SHA-256
setlocal
cd /d "%~dp0"
title Chessboard setup

set "PY_URL=https://www.python.org/ftp/python/3.15.2/python-3.15.2-amd64.exe"
set "SF_URL=https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip"
set "SF_SHA256=3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7"
set "SF_EXE=engines\stockfish\stockfish.exe"
set "SF_WORK=%TEMP%\ChessboardStockfishSetup"

if not exist "chessboard.pyw" goto not_unpacked
if not exist "app\" goto not_unpacked

echo Chessboard setup
echo ================
echo.

rem --- 1. Python 3.15 ---------------------------------------------------------
echo [1/4] Looking for Python 3.15...
set "PY=py -3.15"
%PY% -c "" >nul 2>nul && goto python_ok
set "PY=python"
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 15))" >nul 2>nul && goto python_ok
goto no_python
:python_ok
echo       Found.
echo.

rem --- 2. Pillow --------------------------------------------------------------
echo [2/4] Installing Pillow (image handling)...
if exist "wheels\" goto pillow_offline
%PY% -m pip install --disable-pip-version-check --quiet -r requirements-global.txt
goto pillow_done
:pillow_offline
%PY% -m pip install --disable-pip-version-check --quiet --no-index --find-links wheels -r requirements-global.txt
:pillow_done
if errorlevel 1 goto install_failed
echo       Done.
echo.

rem --- 3. python-chess --------------------------------------------------------
echo [3/4] Installing python-chess (chess rules)...
if exist "vendor\chess\" goto chess_present
%PY% -m pip install --disable-pip-version-check --quiet --target vendor -r requirements-vendor.txt
if errorlevel 1 goto install_failed
:chess_present
%PY% -c "import sys; sys.path.insert(0, 'vendor'); import tkinter, PIL, chess.pgn"
if errorlevel 1 goto install_failed
echo       Done.
echo.

rem --- 4. Stockfish -----------------------------------------------------------
echo [4/4] Setting up Stockfish (the chess engine)...
rem A copy with the wrong name or in a subfolder is moved to the right place first
if exist "%SF_EXE%" goto stockfish_placed
for /r "engines\stockfish" %%F in (stockfish*.exe) do if not exist "%SF_EXE%" move /y "%%F" "%SF_EXE%" >nul
if exist "%SF_EXE%" goto stockfish_placed

echo       Downloading about 80 MB, this can take a few minutes...
if exist "%SF_WORK%" rmdir /s /q "%SF_WORK%"
mkdir "%SF_WORK%"
"%SystemRoot%\System32\curl.exe" -L --fail --retry 2 --ssl-revoke-best-effort --progress-bar -o "%SF_WORK%\stockfish.zip" "%SF_URL%"
if errorlevel 1 goto stockfish_failed
certutil -hashfile "%SF_WORK%\stockfish.zip" SHA256 | findstr /i /c:"%SF_SHA256%" >nul
if errorlevel 1 goto stockfish_failed
"%SystemRoot%\System32\tar.exe" -xf "%SF_WORK%\stockfish.zip" -C "%SF_WORK%"
if errorlevel 1 goto stockfish_failed
for /r "%SF_WORK%" %%F in (stockfish*.exe) do copy /y "%%F" "%SF_EXE%" >nul
rmdir /s /q "%SF_WORK%"
if not exist "%SF_EXE%" goto stockfish_failed

:stockfish_placed
rem A copy unpacked by hand is marked as "from the internet"; so are the bat files
powershell -NoProfile -Command "Unblock-File -Path '%SF_EXE%','Chessboard.bat'" >nul 2>nul
rem Run from Python: a damaged or blocked exe would end this script if cmd started it in a pipe
%PY% -c "import subprocess, sys; r = subprocess.run([r'%SF_EXE%'], input='uci\nquit\n', capture_output=True, text=True, timeout=30); sys.exit('uciok' not in r.stdout)" >nul 2>nul
if errorlevel 1 goto stockfish_not_running
echo       Done: %SF_EXE%
echo.

echo ================================================================
echo  Everything is ready.
echo  Start the program by double-clicking Chessboard.bat
echo ================================================================
echo.
pause
exit /b 0

rem --- Messages ---------------------------------------------------------------
:not_unpacked
echo The program files were not found next to this file.
echo.
echo You are probably still looking inside the zip file. In File Explorer,
echo right-click the zip file, choose "Extract All...", open the new folder
echo and double-click Install.bat there.
echo.
pause
exit /b 1

:no_python
echo.
echo Python 3.15 is not installed. Chessboard needs it to run.
echo.
echo Your web browser will now download the Python installer. Then:
echo   1. Open the downloaded file (python-3.15.2-amd64.exe).
echo   2. Tick "Add python.exe to PATH" at the bottom of the first screen.
echo   3. Click "Install Now". When it has finished, click "Close".
echo   4. Double-click Install.bat again.
echo.
echo If you have just installed Python and still see this, restart the computer.
echo.
pause
start "" "%PY_URL%"
exit /b 1

:install_failed
echo.
echo Setup could not finish. See the messages above.
echo Check your internet connection and run Install.bat again.
echo If it keeps failing, see "If something goes wrong" in INSTALL.txt.
echo.
pause
exit /b 1

:stockfish_failed
if exist "%SF_WORK%" rmdir /s /q "%SF_WORK%"
echo.
echo Stockfish could not be downloaded.
goto stockfish_advice

:stockfish_not_running
echo.
echo %SF_EXE% is there, but it does not run. Your antivirus program may
echo have blocked it, or the file may be damaged.
goto stockfish_advice

:stockfish_advice
echo.
echo Chessboard works without Stockfish, but the computer then only plays
echo random moves. To fix this, run Install.bat again, or follow
echo "Installing Stockfish by hand" in INSTALL.txt.
echo.
pause
exit /b 1
