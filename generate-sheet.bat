@echo off
REM Generate and open the chore checklist HTML
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File generate_sheet.ps1
start chrome "file:///%CD:~3%/checklist.html"
