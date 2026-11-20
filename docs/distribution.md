# 配布方法

| | ポータブル版（おすすめ） | exe 版 |
|---|---|---|
| 配布サイズ | 約 15MB | 約 2GB |
| 受け取った人の初回 | 展開して `start.bat`。数分のセットアップ | 展開して exe を起動 |
| アップデート | 小さな zip を上書き | 毎回 2GB |
| GPU 対応 | GPU・ドライバに合わせて自動選択 | ビルドした CUDA 版に固定 |

どちらも初回起動時にモデル（約 5GB）をダウンロードするため、ネット接続が必要です。

## ポータブル版

```powershell
make_portable.bat   # -> dist\ImageSearch-portable.zip
```

ソースと [uv](https://github.com/astral-sh/uv) だけを同梱した zip を作ります。

### uv.exe の入手先

ダウンロードはせず、手元の uv.exe を次の順に探して同梱します。

1. 環境変数 `UV_EXE`（例: `set UV_EXE=C:\tools\uv.exe`）
2. `tools\uv.exe`
3. PATH 上の `uv.exe`
4. `dist\uv-*.zip`（公式リリースの zip）

### 受け取った人の環境で起きること

`portable\start.bat` が初回に次を行います。すべて展開したフォルダ内に置かれるため、フォルダを削除すればアンインストールできます。

- `.python\` … uv が管理する Python 3.10
- `.venv\` … ライブラリ。PyTorch は `--torch-backend=auto` で GPU・ドライバに合ったものを選択
- `.uv-cache\` … ダウンロードキャッシュ
- `models\` … モデル（同梱の `portable\settings.json` で `model_dir` をフォルダ内に設定）

2 回目以降はセットアップを飛ばしてすぐ起動します。
`requirements.txt` が変わったときだけライブラリを更新します。

## フルパッケージ exe 版

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt --extra-index-url https://download.pytorch.org/whl/cu130
build.bat   # -> dist\ImageSearch\ImageSearch.exe
```

PyInstaller の onedir 形式です（torch + CUDA が大きいため onefile は不可）。
再ビルドすると `dist\ImageSearch` は削除されますが、`settings.json` と `config.json` は引き継がれます。

配布する際は、自分用の `settings.json` と `config.json` を含めない。無ければ初回起動時に既定値で生成されます。
