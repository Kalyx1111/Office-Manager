@echo off
setlocal
cd /d "%~dp0"
title Office Manager - Server Console

echo ============================================================
echo   OFFICE MANAGER - Setup and Launch
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this PC.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    echo IMPORTANT: during install, tick "Add python.exe to PATH".
    echo Then double-click this file again.
    echo.
    pause
    exit /b 1
)

if not exist "data" mkdir "data"

echo Checking/installing required packages (first run only, needs internet)...
python -m pip install -r OMRequirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] Package install failed. Check this PC's internet connection,
    echo then re-run this file. See OM_READ_ME.txt if this PC has no internet.
    echo.
    pause
    exit /b 1
)

echo.
echo First launch takes about 20-30 seconds while it sets up every desk
echo account and writes OM_Login_Credentials.csv in this folder.
echo That file holds everyone's starting password - hand out logins
echo from it, then move it somewhere secure.
echo.
echo This window IS the server. Leave it open while staff are using
echo Office Manager. Closing this window stops the system for everyone.
echo.

start "" cmd /c "timeout /t 25 >nul && start http://localhost:8000"

python OMServer.py

echo.
echo Office Manager has stopped.
pause
