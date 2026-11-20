@echo off
rem Build dist\ImageSearch\ImageSearch.exe (onedir). Rebuilding deletes dist\ImageSearch entirely.
setlocal
cd /d "%~dp0"
if exist "dist\ImageSearch\data" (
  echo [ERROR] dist\ImageSearch\data exists and would be deleted by the rebuild.
  echo         Move it elsewhere and point data_dir in settings.json at it.
  pause
  exit /b 1
)
set "KEEP=%TEMP%\imagesearch_keep"
if exist "%KEEP%" rmdir /s /q "%KEEP%"
mkdir "%KEEP%"
if exist "dist\ImageSearch\settings.json" copy /y "dist\ImageSearch\settings.json" "%KEEP%\" >nul
if exist "dist\ImageSearch\config.json"   copy /y "dist\ImageSearch\config.json"   "%KEEP%\" >nul

".venv\Scripts\python.exe" -m PyInstaller ImageSearch.spec --noconfirm || (pause & exit /b 1)

rem restore previous settings, or seed them from the dev copy
if exist "%KEEP%\settings.json" (copy /y "%KEEP%\settings.json" "dist\ImageSearch\" >nul) else if exist settings.json copy /y settings.json "dist\ImageSearch\" >nul
if exist "%KEEP%\config.json"   (copy /y "%KEEP%\config.json"   "dist\ImageSearch\" >nul) else if exist config.json   copy /y config.json   "dist\ImageSearch\" >nul
rmdir /s /q "%KEEP%"
echo.
echo Done: dist\ImageSearch\ImageSearch.exe
