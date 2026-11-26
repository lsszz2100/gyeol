@echo off
setlocal
cd /d "%~dp0"
title GYEOL Installer Builder

set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
set "B=%TEMP%\gyeol_build"
"%PY%" make_code.py
if errorlevel 1 goto fail
set /p VER=<version.txt

echo [1/2] Building Gyeol.exe (version %VER%) ...
if exist "%B%" rmdir /s /q "%B%"
mkdir "%B%"
"%PY%" -m PyInstaller --name=Gyeol --onedir --noconsole --clean --noconfirm ^
    --collect-data pptx --collect-all playwright --collect-all imageio_ffmpeg ^
    --exclude-module pymupdf.layout --exclude-module pymupdf4llm --exclude-module onnxruntime ^
    --icon="%~dp0app.ico" ^
    --add-data="%~dp0build_code;appcode" ^
    --add-data="%~dp0runtime.txt;." ^
    --specpath "%B%" --workpath "%B%\work" --distpath "%B%\dist" ^
    "%~dp0..\launcher.py"
if errorlevel 1 goto fail

set "SUF="
if "%GYEOL_RETAIL%"=="1" (
  echo {"edition":"retail"}> "%B%\dist\Gyeol\edition.json"
  set "SUF=-retail"
  echo   retail edition: subscription CLI login blocked, API key only
)
echo [2/2] Building installer ...
"%ISCC%" /Q /DAppVersion=%VER% /DSuffix=%SUF% /DDistDir="%B%\dist\Gyeol" installer.iss
if errorlevel 1 goto fail

echo.
echo [DONE] packaging\output\Gyeol-Setup-%VER%%SUF%.exe
if not "%1"=="nopause" pause
exit /b 0

:fail
echo [FAILED]
if not "%1"=="nopause" pause
exit /b 1
