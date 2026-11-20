# 画像検索サーバーを起動し、ブラウザで開く。 -Reindex を付けると先に差分インデックス更新を行う。
param([switch]$Reindex)
Set-Location $PSScriptRoot
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = 1
if ($Reindex) { & .\.venv\Scripts\python.exe index.py }
Start-Job { Start-Sleep 25; Start-Process "http://127.0.0.1:5055" } | Out-Null
& .\.venv\Scripts\python.exe app.py
