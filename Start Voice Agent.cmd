@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" "%~dp0voice_test.py"
if errorlevel 1 pause
