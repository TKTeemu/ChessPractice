@echo off
rem Starts Chessboard without a console window: with the py launcher (Python 3.15)
rem if it is installed, otherwise with pythonw from PATH.
cd /d "%~dp0"
py -3.15 -c "" >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3.15 chessboard.pyw
    exit /b
)
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw chessboard.pyw
    exit /b
)
echo Python 3.15 was not found.
echo Double-click Install.bat first. INSTALL.txt has the full instructions.
pause
