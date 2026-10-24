@echo off
chcp 65001 >nul
title DraveSound - een Dravenlock product
cd /d "%~dp0"
set "LOG=start-log.txt"
> "%LOG%" echo DraveSound start-log

set "PYEXE="
for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined PYEXE ( py -%%V -c "import sys" >nul 2>&1 && set "PYEXE=py -%%V" )
)
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
    echo Geen Python gevonden. Installeer Python 3.10+ van python.org
    pause & exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Eerste keer: omgeving opzetten...
    %PYEXE% -m venv .venv >> "%LOG%" 2>&1
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >> "%LOG%" 2>&1
    ".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt >> "%LOG%" 2>&1
)

".venv\Scripts\python.exe" -c "import sounddevice, soundfile, numpy, PyQt5" >nul 2>&1
if errorlevel 1 (
    echo Nieuwe onderdelen installeren...
    ".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt >> "%LOG%" 2>&1
)

echo DraveSound wordt gestart...
".venv\Scripts\python.exe" dravesound.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [FOUT] DraveSound is met een fout gestopt. Stuur start-log.txt naar service@dravenlock.nl
    pause
)
