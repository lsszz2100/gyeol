@echo off
rem GYEOL retail (for sale) installer: same build, edition.json = retail, output Gyeol-Setup-<ver>-retail.exe
setlocal
set "GYEOL_RETAIL=1"
call "%~dp0build_installer.bat" %*
exit /b %errorlevel%
