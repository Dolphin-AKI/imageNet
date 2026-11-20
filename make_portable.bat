@echo off
rem Build dist\ImageSearch-portable.zip : source + uv.exe (no bundled Python/torch).
rem The recipient runs start.bat, which installs everything on first launch.
rem
rem uv.exe is taken from a local copy (no download). Search order:
rem   1. %UV_EXE%              (set UV_EXE=C:\path\to\uv.exe)
rem   2. tools\uv.exe
rem   3. uv.exe on PATH
rem   4. dist\uv-*.zip         (official release zip)
setlocal
cd /d "%~dp0"
set "NAME=ImageSearch-portable"
set "OUT=dist\%NAME%"
set "SEVENZIP=%ProgramFiles%\7-Zip\7z.exe"
set "TAR=%SystemRoot%\System32\tar.exe"

set "UVSRC="
if defined UV_EXE if exist "%UV_EXE%" set "UVSRC=%UV_EXE%"
if not defined UVSRC if exist "tools\uv.exe" set "UVSRC=tools\uv.exe"
if not defined UVSRC for %%p in (uv.exe) do if not "%%~$PATH:p"=="" set "UVSRC=%%~$PATH:p"
set "UVZIP="
if not defined UVSRC for %%z in (dist\uv-*.zip) do set "UVZIP=%%z"
if not defined UVSRC if not defined UVZIP (
  echo [ERROR] uv.exe not found. Set UV_EXE, or put uv.exe in tools\.
  pause
  exit /b 1
)

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%\static"
if defined UVSRC (
  echo uv: %UVSRC%
  copy /y "%UVSRC%" "%OUT%\uv.exe" >nul || (echo [ERROR] failed to copy uv.exe & pause & exit /b 1)
) else (
  echo uv: %UVZIP%
  "%TAR%" -xf "%UVZIP%" -C "%OUT%" uv.exe || (echo [ERROR] failed to extract uv.exe & pause & exit /b 1)
)
"%OUT%\uv.exe" --version

for %%f in (app.py common.py index.py main.py requirements.txt) do copy /y "%%f" "%OUT%\" >nul
copy /y static\index.html "%OUT%\static\" >nul
for %%f in (start.bat settings.json README.txt) do copy /y "portable\%%f" "%OUT%\" >nul

if exist "dist\%NAME%.zip" del "dist\%NAME%.zip"
pushd dist
if exist "%SEVENZIP%" (
  "%SEVENZIP%" a -tzip -mx=9 -bso0 -bsp0 "%NAME%.zip" "%NAME%" || (popd & pause & exit /b 1)
) else (
  "%TAR%" -a -cf "%NAME%.zip" "%NAME%" || (popd & pause & exit /b 1)
)
popd
echo.
echo Done: dist\%NAME%.zip
