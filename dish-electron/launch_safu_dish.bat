@echo off
title SAFU DISH Launcher
setlocal enabledelayedexpansion

:: Resolve launch directory
for %%I in ("%~dp0") do set "LAUNCHDIR=%%~fI"
set "LAUNCHDIR=%LAUNCHDIR:~0,-1%"

:: If launched from dish-electron, move up to SAFU NOVA root
for %%I in ("%LAUNCHDIR%") do set "CURRENTFOLDER=%%~nxI"

if /I "!CURRENTFOLDER!"=="dish-electron" (
    for %%I in ("!LAUNCHDIR!\..") do set "BASEPATH=%%~fI"
) else (
    set "BASEPATH=!LAUNCHDIR!"
)

set "BACKEND=!BASEPATH!\safu_dish_backend"
set "FRONTEND=!BASEPATH!\safu_dish_frontend"

set "WINPYTHON=!BASEPATH!\WPy64-31180\python-3.11.8.amd64\python.exe"
set "VENV=!BACKEND!\venv"
set "VENV_PYTHON=!VENV!\Scripts\python.exe"

set "NODEDIR=!BASEPATH!\node"
set "NODE=!NODEDIR!\node.exe"
set "NPM=!NODEDIR!\npm.cmd"
set "PATH=!NODEDIR!;!PATH!"

set "USERDATA=!BASEPATH!\userdata"

set "DISH_PORTABLE=1"
set "DISH_ROOT=!BASEPATH!"
set "DISH_USERDATA=!USERDATA!"
set "PYTHONNOUSERSITE=1"
set "PYTHONPYCACHEPREFIX=!USERDATA!\pycache"
set "TEMP=!USERDATA!\temp"
set "TMP=!USERDATA!\temp"

if not exist "!USERDATA!" mkdir "!USERDATA!"
if not exist "!USERDATA!\temp" mkdir "!USERDATA!\temp"
if not exist "!USERDATA!\pycache" mkdir "!USERDATA!\pycache"

if not exist "!WINPYTHON!" (
    echo [ERROR] WinPython not found:
    echo !WINPYTHON!
    pause
    exit /b 1
)

if not exist "!NODE!" (
    echo [ERROR] Portable node.exe not found:
    echo !NODE!
    pause
    exit /b 1
)

if not exist "!NPM!" (
    echo [ERROR] Portable npm.cmd not found:
    echo !NPM!
    pause
    exit /b 1
)

if not exist "!BACKEND!\main.py" (
    echo [ERROR] Backend main.py not found:
    echo !BACKEND!\main.py
    pause
    exit /b 1
)

if not exist "!FRONTEND!\package.json" (
    echo [ERROR] Frontend package.json not found:
    echo !FRONTEND!\package.json
    pause
    exit /b 1
)

:: Check if venv is missing or poisoned by system Python
set "REBUILD_VENV=0"

if not exist "!VENV_PYTHON!" (
    set "REBUILD_VENV=1"
)

if exist "!VENV!\pyvenv.cfg" (
    findstr /I /C:"C:\Program Files" "!VENV!\pyvenv.cfg" >nul
    if not errorlevel 1 set "REBUILD_VENV=1"

    findstr /I /C:"C:\Users" "!VENV!\pyvenv.cfg" >nul
    if not errorlevel 1 set "REBUILD_VENV=1"
)

if "!REBUILD_VENV!"=="1" (
    echo [LAUNCHER] Rebuilding backend venv with internal WinPython...

    if exist "!VENV!" (
        rmdir /s /q "!VENV!"
    )

    "!WINPYTHON!" -m venv "!VENV!"

    if errorlevel 1 (
        echo [ERROR] Failed to rebuild backend venv.
        pause
        exit /b 1
    )

    echo [LAUNCHER] Installing backend requirements...

    "!VENV_PYTHON!" -m pip install --upgrade pip setuptools wheel

    if exist "!BACKEND!\requirements.txt" (
        "!VENV_PYTHON!" -m pip install -r "!BACKEND!\requirements.txt"
    )
)

echo [LAUNCHER] Root: !BASEPATH!
echo [LAUNCHER] Backend: !BACKEND!
echo [LAUNCHER] Frontend: !FRONTEND!
echo [LAUNCHER] Python: !VENV_PYTHON!
echo [LAUNCHER] NPM: !NPM!

echo [LAUNCHER] Launching BACKEND...
start "SAFU DISH BACKEND - uvicorn" ^
cmd /k "cd /d "!BACKEND!" && "!VENV_PYTHON!" -m uvicorn main:app --reload"

echo [LAUNCHER] Launching FRONTEND...
start "SAFU DISH FRONTEND" ^
cmd /k "cd /d "!FRONTEND!" && "!NPM!" run dev"

exit