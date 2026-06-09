@echo off
title Document De-identifier
cd /d "%~dp0"

echo ============================================================
echo   Document De-identifier  -  starting up...
echo.
echo   A browser tab will open automatically in a few seconds.
echo   Keep THIS black window open while you use the app.
echo   To stop the app, close this window.
echo ============================================================
echo.

REM Run the app using the bundled Python. No system Python required.
REM The app opens your default browser itself once it's ready.
set PYTHONUTF8=1
REM Keep the entity dictionary + vault inside this portable folder (so the data
REM travels with the bundle) rather than the per-user app-data directory.
set "LETHE_DATA_DIR=%~dp0data"
"runtime\python.exe" app.py

echo.
echo The app has stopped. You can close this window.
pause
