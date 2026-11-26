@echo off
setlocal
cd /d "%~dp0"
title GYEOL - AI Presentation
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ======================================================================
echo    GYEOL - AI Presentation
echo ======================================================================
echo.

:: 1. Find Python (prefer per-user installs)
set "PY_CMD="
for %%V in (312 311 310 313) do (
    if not defined PY_CMD if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python%%V\python.exe"
)
if defined PY_CMD goto :PYTHON_FOUND

for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PY_CMD set "PY_CMD=%%P"
)
if defined PY_CMD goto :PYTHON_FOUND

echo [ERROR] Python not found.
echo Install Python 3.12 from https://www.python.org and try again.
pause
exit /b 1

:PYTHON_FOUND
echo [*] Python: %PY_CMD%

:: 2. Install missing packages (first run only)
"%PY_CMD%" -c "import webview, pptx, pymupdf, playwright" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required packages - first run only...
    "%PY_CMD%" -m pip install -q -r requirements.txt
)
echo [*] Starting GYEOL...
echo.

:: 3. app.py starts the server and opens the app window itself
"%PY_CMD%" app.py
if errorlevel 1 (
    echo.
    echo [ERROR] GYEOL exited with an error. See messages above.
)

pause
