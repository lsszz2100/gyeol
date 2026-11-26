@echo off
rem GYEOL release: bump version.py, edit release_notes.txt, run this file.
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
call "%~dp0build_installer.bat" nopause || goto :fail
set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0make_release.py" full || goto :fail
exit /b 0
:fail
echo [FAILED]
exit /b 1
