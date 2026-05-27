@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "update-site.ps1"
