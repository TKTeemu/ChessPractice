@echo off
rem Starts Chessboard without a console window: with the py launcher (Python 3.15)
rem if it is installed, otherwise with pythonw from PATH.
cd /d "%~dp0"
py -3.15 -c "" >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3.15 shakkilauta.pyw
    exit /b
)
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw shakkilauta.pyw
    exit /b
)
echo Python 3.15 was not found.
echo Install it from https://www.python.org/downloads/ and run this file again.
pause
