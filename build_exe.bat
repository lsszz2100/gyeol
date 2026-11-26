@echo off
setlocal
cd /d "%~dp0"
title GYEOL EXE Builder

echo ======================================================================
echo    GYEOL - Standalone EXE Builder
echo ======================================================================
echo.

set "PY_CMD="
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
) else (
    set "PY_CMD=python"
)

echo [*] Installing PyInstaller and pywebview...
"%PY_CMD%" -m pip install pyinstaller -r requirements.txt >nul 2>&1

echo [*] Building Gyeol.exe...
"%PY_CMD%" -m PyInstaller ^
    --name="Gyeol" ^
    --onedir ^
    --noconsole ^
    --clean ^
    --collect-data pptx ^
    --collect-all playwright ^
    --exclude-module pymupdf.layout ^
    --exclude-module pymupdf4llm ^
    --exclude-module onnxruntime ^
    --icon="static\img\app.ico" ^
    --add-data="%~dp0static;static" ^
    --add-data="%~dp0core\themes.json;core" ^
    --add-data="%~dp0core\theme_legacy.json;core" ^
    --add-data="%~dp0core\advisor_data.json;core" ^
    "%~dp0app.py"

echo.
echo ======================================================================
echo  [DONE] Created dist\Gyeol\Gyeol.exe
echo  Zip the dist\Gyeol folder to distribute.
echo ======================================================================
pause
