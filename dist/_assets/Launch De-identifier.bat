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
"runtime\python.exe" app.py

echo.
echo The app has stopped. You can close this window.
pause
