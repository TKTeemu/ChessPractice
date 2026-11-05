@echo off
rem Starts Chessboard without a console window, with the Python environment Install.bat creates.
cd /d "%~dp0"
".venv\Scripts\python.exe" -c "" >nul 2>nul
if errorlevel 1 goto not_set_up
start "" ".venv\Scripts\pythonw.exe" chessboard.pyw
exit /b

:not_set_up
echo Chessboard is not set up yet, or its setup no longer works.
echo Double-click Install.bat first. INSTALL.txt has the full instructions.
pause
