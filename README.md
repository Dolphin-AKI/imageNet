# image-search

多言語 CLIP（`xlm-roberta-large-ViT-H-14`）を使ったローカル画像検索ツール。
指定フォルダ内の画像をインデックス化し、日本語を含むテキストでブラウザから検索できます。

## セットアップ

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
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

## exe ビルド

```powershell
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
