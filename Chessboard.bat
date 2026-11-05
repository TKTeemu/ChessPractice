@echo off
rem Starts Chessboard without a console window, with Python 3.15 found in the same places
rem as Install.bat: the py launcher, PATH, and the folders the python.org installer uses.
cd /d "%~dp0"
py -3.15 -c "" >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3.15 chessboard.pyw
    exit /b
)
where pythonw >nul 2>nul
if errorlevel 1 goto install_folders
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 15))" >nul 2>nul
if errorlevel 1 goto install_folders
start "" pythonw chessboard.pyw
exit /b

:install_folders
if exist "%LOCALAPPDATA%\Programs\Python\Python315\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python315\pythonw.exe" chessboard.pyw
    exit /b
)
if exist "%ProgramFiles%\Python315\pythonw.exe" (
    start "" "%ProgramFiles%\Python315\pythonw.exe" chessboard.pyw
    exit /b
)
echo Python 3.15 was not found.
echo Double-click Install.bat first. INSTALL.txt has the full instructions.
pause
