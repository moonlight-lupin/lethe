@echo off
REM Double-click to start the De-identifier. A browser tab will open.
REM Close this black window to stop the app.
cd /d "%~dp0"
set PYTHONUTF8=1
".venv313\Scripts\python.exe" app.py
echo.
echo The app has stopped. You can close this window.
pause
