@echo off
rem Image search launcher
rem   start.bat            : start server and open browser
rem   start.bat /reindex   : update index first, then start
setlocal
cd /d "%~dp0"
set "URL=http://127.0.0.1:5055"
set "PY=%~dp0.venv\Scripts\python.exe"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONIOENCODING=utf-8

if not exist "%PY%" (
  echo [エラー] Python 仮想環境が見つかりません: %PY%
  pause
  exit /b 1
)

rem already running -> just open the browser
curl.exe -s -o nul "%URL%/api/info" && (
  echo 画像検索サーバーは既に起動しています。ブラウザを開きます。
  start "" "%URL%"
  exit /b 0
)

if /i "%~1"=="/reindex" (
  echo インデックスを更新しています...
  "%PY%" index.py || (echo [エラー] インデックス更新に失敗しました & pause & exit /b 1)
)

echo 画像検索サーバーを起動しています（モデル読み込みに20-30秒かかります）...
echo 終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。
echo.

rem open the browser once the server answers
start "" /b cmd /q /c "for /l %%i in (1,1,120) do (curl.exe -s -o nul %URL%/api/info && (start "" %URL% & exit) || timeout /t 1 /nobreak >nul)"

"%PY%" app.py
if errorlevel 1 pause
