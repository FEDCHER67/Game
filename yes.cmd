@echo off
cd /d "%~dp0"
echo APPROVE_PENDING_TASK=YES| opencode.cmd run --agent deepseek-committer
exit /b %ERRORLEVEL%
