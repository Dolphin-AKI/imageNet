# image-search

多言語 CLIP（`xlm-roberta-large-ViT-H-14`）を使ったローカル画像検索ツール。
指定フォルダ内の画像をインデックス化し、日本語を含むテキストでブラウザから検索できます。

## セットアップ

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu130
copy settings.example.json settings.json
copy config.example.json config.json
```

- `config.json` … インデックス対象フォルダ（`roots`）
- `settings.json` … データ保存先 `data_dir`、モデルキャッシュ `model_dir`、ポート `port` など

どちらも無ければ初回起動時に自動生成されます。初回はモデル（約 5GB）がダウンロードされます。

## 使い方

```powershell
start.bat            # サーバー起動 + ブラウザを開く (http://127.0.0.1:5055)
start.bat /reindex   # 先に差分インデックス更新
python index.py --full   # インデックスを作り直す
```

## 配布

### ポータブル版（おすすめ・約 15MB）

```powershell
make_portable.bat   # -> dist\ImageSearch-portable.zip
```

ソースと [uv](https://github.com/astral-sh/uv) だけを同梱した zip を作ります。
uv.exe はダウンロードせず手元のものを使います（`UV_EXE` → `tools\uv.exe` → PATH → `dist\uv-*.zip` の順に探索）。
受け取った人は展開して `start.bat` を実行するだけで、初回に Python・ライブラリ
（GPU/ドライバに合った PyTorch を自動選択）・モデルがフォルダ内にダウンロードされます。
アップデート時は `requirements.txt` が変わったときだけライブラリが更新されます。

### exe 版（約 2GB）

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt --extra-index-url https://download.pytorch.org/whl/cu130
build.bat   # -> dist\ImageSearch\ImageSearch.exe
```

## 構成

| ファイル | 内容 |
|---|---|
| `app.py` | Flask サーバー / 検索 API |
| `index.py` | 画像の埋め込み・サムネイル生成（差分更新） |
| `common.py` | 設定読み込み・モデルロード |
| `main.py` | exe 用エントリーポイント |
| `static/index.html` | フロントエンド |
| `ImageSearch.spec` | PyInstaller 設定 |
| `portable/` | ポータブル版の起動 bat・設定・同梱 README |
| `make_portable.bat` | ポータブル版 zip の作成 |
