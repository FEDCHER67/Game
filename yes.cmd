@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\agents\yes.ps1"
exit /b %ERRORLEVEL%
