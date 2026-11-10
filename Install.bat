@echo off
rem Sets up Chessboard after unpacking. Safe to run again: it only does what is still missing.
rem   Install.bat       installs what the program needs
rem   Install.bat dev   also installs the test tools, for developers
rem Everything goes into this folder, nothing outside it: no installer, no registry, no PATH.
rem   1. unpacks the official Windows embeddable package of Python into the folder python
rem      (again if it is missing, damaged or another version), with setup\python315._pth
rem   2. adds Tcl/Tk and tkinter to it from the official tcltk.msi of the same release
rem      (an administrative install, which only copies files: nothing is registered)
rem   3. installs pip from its wheel, then the libraries in requirements.txt into
rem      python\Lib\site-packages, from the wheels folder and PyPI (only from wheels if it has
rem      Pillow too, as in a distribution zip)
rem   4. puts Stockfish at engines\stockfish\stockfish.exe: fixes a wrong name or subfolder,
rem      otherwise downloads the release below
rem Every download is checked against its SHA-256 below. A new Python release: see
rem docs\MAINTENANCE.md, "A new Python 3.15.x".
setlocal
cd /d "%~dp0"
title Chessboard setup

set "PY_VERSION=3.15.2"
set "PY_EMBED_URL=https://www.python.org/ftp/python/3.15.2/python-3.15.2-embed-amd64.zip"
set "PY_EMBED_SHA256=d012f3aa29cf07436dae8aea1fec0fd195c2612a0b059b1f915ae0afb9ad1f62"
set "TCLTK_URL=https://www.python.org/ftp/python/3.15.2/amd64/tcltk.msi"
set "TCLTK_SHA256=a398763af9d67cb6b0bef4326c5538de4363b8560413d0cc5604344d487bcc62"
set "PIP_WHEEL_URL=https://files.pythonhosted.org/packages/07/25/ee8c38ae72d66b844ce8eb9711ba905dba21ca1a8a0c960057c41cd23337/pip-26.3-py3-none-any.whl"
set "PIP_WHEEL_SHA256=f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13"
set "PY_DIR=python"
set "PY_EXE=python\python.exe"
set "PY_PTH=python315._pth"
set "SF_URL=https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip"
set "SF_SHA256=3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7"
set "SF_EXE=engines\stockfish\stockfish.exe"
set "WORK=%TEMP%\ChessboardSetup"
set "REQUIREMENTS=requirements.txt"
if /i "%~1"=="dev" set "REQUIREMENTS=requirements-dev.txt"
set "NO_INDEX="
if exist "wheels\pillow-*.whl" set "NO_INDEX=--no-index"

if not exist "chessboard.pyw" goto not_unpacked
if not exist "app\" goto not_unpacked
if not exist "setup\%PY_PTH%" goto not_unpacked

rem Under e.g. C:\Program Files nothing can be written without administrator rights
copy /y nul "install-test.tmp" >nul 2>nul
if not exist "install-test.tmp" goto not_writable
del "install-test.tmp"

echo Chessboard setup
echo ================
echo.

rem --- 1. Python ------------------------------------------------------------
echo [1/4] Setting up Python %PY_VERSION% in the folder %PY_DIR%...
"%PY_EXE%" -c "import sys; sys.exit(sys.version.split()[0] != '%PY_VERSION%')" >nul 2>nul
if not errorlevel 1 goto python_present
if not exist "%PY_DIR%\" goto python_download
echo       The Python there is damaged or another version, so it is set up again.
rmdir /s /q "%PY_DIR%" >nul 2>nul
if exist "%PY_DIR%\" goto python_locked
:python_download
echo       Downloading about 14 MB...
call :download "%PY_EMBED_URL%" "%PY_EMBED_SHA256%" "python.zip"
if errorlevel 1 goto download_failed
mkdir "%PY_DIR%"
"%SystemRoot%\System32\tar.exe" -xf "%WORK%\python.zip" -C "%PY_DIR%"
if errorlevel 1 goto install_failed
copy /y "setup\%PY_PTH%" "%PY_DIR%\" >nul
"%PY_EXE%" -c "" >nul 2>nul
if errorlevel 1 goto python_not_running
echo       Done.
goto python_done
:python_present
rem The path file can change in a new version of Chessboard, so it is always copied
copy /y "setup\%PY_PTH%" "%PY_DIR%\" >nul
echo       Already there.
:python_done
rem From a zip made with --with-python, every file in python is marked as "from the internet"
rem by Extract All, and pythonw.exe could then show a security warning or be blocked
powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%PY_DIR%' -Recurse -File | Unblock-File" >nul 2>nul
echo.

rem --- 2. Tcl/Tk --------------------------------------------------------------
echo [2/4] Adding Tcl/Tk, which draws the program's window...
"%PY_EXE%" -c "import tkinter; tkinter.Tk().destroy()" >nul 2>nul
if not errorlevel 1 goto tcltk_present
echo       Downloading about 5 MB...
call :download "%TCLTK_URL%" "%TCLTK_SHA256%" "tcltk.msi"
if errorlevel 1 goto download_failed
rem /a only copies the files into TARGETDIR (an absolute path); nothing is registered
start "" /wait "%SystemRoot%\System32\msiexec.exe" /a "%WORK%\tcltk.msi" /qn TARGETDIR="%CD%\%PY_DIR%" /l* "%WORK%\tcltk.log"
if errorlevel 1 goto tcltk_failed
rem Not needed: the copy of the msi, IDLE, the turtle demos, tests and C import libraries
if exist "%PY_DIR%\tcltk.msi" del "%PY_DIR%\tcltk.msi"
for %%D in (Lib\idlelib Lib\turtledemo Lib\test libs) do if exist "%PY_DIR%\%%D\" rmdir /s /q "%PY_DIR%\%%D"
"%PY_EXE%" -c "import tkinter; tkinter.Tk().destroy()"
if errorlevel 1 goto tcltk_failed
echo       Done.
goto tcltk_done
:tcltk_present
echo       Already there.
:tcltk_done
echo.

rem --- 3. Libraries -----------------------------------------------------------
echo [3/4] Installing the libraries Chessboard needs...
"%PY_EXE%" setup\check_libraries.py %REQUIREMENTS% >nul 2>nul
if not errorlevel 1 goto libraries_present
"%PY_EXE%" -m pip --version >nul 2>nul
if not errorlevel 1 goto pip_ready
rem A wheel is a zip: unpacked into site-packages, pip is installed (pip will not install
rem itself from its own wheel on Windows)
echo       Downloading pip, the library installer, about 2 MB...
call :download "%PIP_WHEEL_URL%" "%PIP_WHEEL_SHA256%" "pip.whl"
if errorlevel 1 goto download_failed
if not exist "%PY_DIR%\Lib\site-packages\" mkdir "%PY_DIR%\Lib\site-packages"
"%SystemRoot%\System32\tar.exe" -xf "%WORK%\pip.whl" -C "%PY_DIR%\Lib\site-packages"
if errorlevel 1 goto install_failed
:pip_ready
rem --isolated: pip settings of another Python on this computer are not used
rem --no-cache-dir: no cache in %LOCALAPPDATA%\pip; the requirements pin every hash anyway
"%PY_EXE%" -m pip install --isolated --no-cache-dir --disable-pip-version-check --no-warn-script-location --quiet --only-binary :all: --find-links wheels %NO_INDEX% -r %REQUIREMENTS%
if errorlevel 1 goto install_failed
"%PY_EXE%" setup\check_libraries.py %REQUIREMENTS%
if errorlevel 1 goto install_failed
echo       Done.
goto libraries_done
:libraries_present
echo       Already there.
:libraries_done
if exist "%WORK%" rmdir /s /q "%WORK%"
rem The environment of older versions of Chessboard
if not exist ".venv\" goto venv_gone
rmdir /s /q ".venv" >nul 2>nul
if not exist ".venv\" echo       The old Python environment .venv was removed; it is no longer needed.
:venv_gone
echo.

rem --- 4. Stockfish -----------------------------------------------------------
echo [4/4] Setting up Stockfish (the chess engine)...
rem A copy with the wrong name or in a subfolder is moved to the right place first
if exist "%SF_EXE%" goto stockfish_placed
for /r "engines\stockfish" %%F in (stockfish*.exe) do if not exist "%SF_EXE%" move /y "%%F" "%SF_EXE%" >nul
if exist "%SF_EXE%" goto stockfish_placed

echo       Downloading about 80 MB, this can take a few minutes...
call :download "%SF_URL%" "%SF_SHA256%" "stockfish.zip"
if errorlevel 1 goto stockfish_failed
"%SystemRoot%\System32\tar.exe" -xf "%WORK%\stockfish.zip" -C "%WORK%"
if errorlevel 1 goto stockfish_failed
for /r "%WORK%" %%F in (stockfish*.exe) do copy /y "%%F" "%SF_EXE%" >nul
rmdir /s /q "%WORK%"
if not exist "%SF_EXE%" goto stockfish_failed

:stockfish_placed
rem A copy unpacked by hand is marked as "from the internet"; so are the bat files
powershell -NoProfile -Command "Unblock-File -Path '%SF_EXE%','Chessboard.bat'" >nul 2>nul
rem Run from Python: a damaged or blocked exe would end this script if cmd started it in a pipe
"%PY_EXE%" -c "import subprocess, sys; r = subprocess.run([r'%SF_EXE%'], input='uci\nquit\n', capture_output=True, text=True, timeout=30); sys.exit('uciok' not in r.stdout)" >nul 2>nul
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

rem --- Downloading --------------------------------------------------------------
rem call :download URL SHA256 NAME   ->  %WORK%\NAME, from an empty %WORK%; errorlevel 1 if the
rem download failed or the file is not the expected one
:download
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"
"%SystemRoot%\System32\curl.exe" -L --fail --retry 2 --ssl-revoke-best-effort --progress-bar -o "%WORK%\%~3" "%~1"
if errorlevel 1 exit /b 1
certutil -hashfile "%WORK%\%~3" SHA256 | findstr /i /c:"%~2" >nul
if errorlevel 1 exit /b 1
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

:not_writable
echo Chessboard cannot save files in this folder:
echo   %CD%
echo.
echo Move the Chessboard folder to Documents and run Install.bat again.
echo.
pause
exit /b 1

:python_locked
echo.
echo The folder %PY_DIR% could not be replaced because a file in it is in use.
echo Close Chessboard if it is open, then run Install.bat again.
echo.
pause
exit /b 1

:download_failed
if exist "%WORK%" rmdir /s /q "%WORK%"
echo.
echo The download did not work, or the downloaded file was not the right one.
echo Check your internet connection and run Install.bat again.
echo If it keeps failing, see "If something goes wrong" in INSTALL.txt.
echo.
pause
exit /b 1

:python_not_running
echo.
echo Python was unpacked into the folder %PY_DIR%, but it does not start.
echo Your antivirus program may have blocked python.exe.
echo See "If something goes wrong" in INSTALL.txt.
echo.
pause
exit /b 1

:tcltk_failed
echo.
echo Adding Tcl/Tk, part 2 of the setup, did not work. Windows Installer may be busy with
echo another installation: wait a moment and run Install.bat again.
echo If it keeps failing, see "If something goes wrong" in INSTALL.txt.
echo The details are in %WORK%\tcltk.log
echo.
pause
exit /b 1

:install_failed
if exist "%WORK%" rmdir /s /q "%WORK%"
echo.
echo Setup could not finish. See the messages above.
echo Check your internet connection and run Install.bat again.
echo If it keeps failing, see "If something goes wrong" in INSTALL.txt.
echo.
pause
exit /b 1

:stockfish_failed
if exist "%WORK%" rmdir /s /q "%WORK%"
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
