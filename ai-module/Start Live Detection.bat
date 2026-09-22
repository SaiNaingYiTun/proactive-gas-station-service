@echo off
rem Opens the live detection window (no console window stays open).
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Could not find .venv\Scripts\pythonw.exe next to this file.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" app.py
