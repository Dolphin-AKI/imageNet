@echo off
chcp 65001 >nul
rem Image search launcher (portable / uv edition)
rem   start.bat             : start server and open browser
rem   start.bat --reindex   : update index first, then start
rem First run downloads Python and libraries (a few GB) into this folder.
setlocal
cd /d "%~dp0"
set "UV=%~dp0uv.exe"
set "PY=%~dp0.venv\Scripts\python.exe"
set "STAMP=%~dp0.venv\installed-requirements.txt"
rem keep Python, packages and the download cache inside this folder
set "UV_PYTHON_INSTALL_DIR=%~dp0.python"
set "UV_CACHE_DIR=%~dp0.uv-cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONIOENCODING=utf-8

if not exist "%UV%" (
  echo [エラー] uv.exe が見つかりません: %UV%
  goto fail
)

if not exist "%PY%" (
  echo === 初回セットアップ: Python を準備しています ===
  "%UV%" venv --python 3.10 .venv || goto fail
)

rem install / update libraries when requirements.txt changed
fc /b requirements.txt "%STAMP%" >nul 2>&1
if errorlevel 1 (
  echo === ライブラリをインストールしています（初回は数分かかります）===
  "%UV%" pip install --python "%PY%" --torch-backend=auto -r requirements.txt || goto fail
  copy /y requirements.txt "%STAMP%" >nul
  echo.
)

"%PY%" main.py %*
if errorlevel 1 pause
exit /b 0

:fail
echo.
echo [エラー] セットアップに失敗しました。ネット接続を確認して、もう一度 start.bat を実行してください。
pause
exit /b 1
