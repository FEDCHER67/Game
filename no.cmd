@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\agents\no.ps1"
exit /b %ERRORLEVEL%
