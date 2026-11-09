@echo off
rem Starts Chessboard without a console window, with the Python that Install.bat puts in the
rem folder python. It ignores any other Python on the computer (see setup\python315._pth).
cd /d "%~dp0"
"python\python.exe" -c "" >nul 2>nul
if errorlevel 1 goto not_set_up
start "" "python\pythonw.exe" chessboard.pyw
exit /b

:not_set_up
echo Chessboard is not set up yet, or its setup no longer works.
echo Double-click Install.bat first. INSTALL.txt has the full instructions.
pause
