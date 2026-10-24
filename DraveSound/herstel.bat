@echo off
chcp 65001 >nul
title DraveSound - Herstel
cd /d "%~dp0"
echo Dit verwijdert de .venv-map; bij de volgende start wordt alles opnieuw opgezet.
pause
if exist ".venv" rmdir /s /q ".venv"
echo Klaar. Start DraveSound opnieuw met run.bat
pause
