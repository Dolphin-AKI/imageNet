# 構成

## ファイル構成

| ファイル | 内容 |
|---|---|
| `app.py` | Flask サーバー / 検索 API |
| `index.py` | 画像の埋め込み・サムネイル生成（差分更新） |
| `common.py` | 設定読み込み・モデルロード |
| `main.py` | exe 版・ポータブル版のエントリーポイント |
| `static/index.html` | フロントエンド |
| `start.bat` / `run.ps1` | 開発用の起動スクリプト |
| `build.bat` / `ImageSearch.spec` | exe 版のビルド（PyInstaller） |
| `make_portable.bat` / `portable/` | ポータブル版の作成と同梱ファイル |
| `requirements.txt` | 実行に必要なライブラリ |
| `requirements-build.txt` | exe ビルド用（実行用 + PyInstaller） |

## モデル

- `xlm-roberta-large-ViT-H-14`（`frozen_laion5b_s13b_b90k`）を open_clip 経由で使用
- テキスト側が多言語対応のため、日本語で検索できます
- GPU があれば fp16 で動作します

## インデックス

`data_dir` に次のファイルを保存します。

| ファイル | 内容 |
|---|---|
| `embeddings.npy` | 画像の埋め込みベクトル |
| `meta.json` | パス・更新日時・サイズ・サムネイル名など |
| `thumbs/` | サムネイル（最大 320px） |
| `concepts.json` | ラベルと見本画像 |

更新日時とサイズが変わったファイルだけを再計算します。
削除された画像や、設定から外したフォルダの画像はインデックスから除かれます。

## セキュリティ

サーバーは自分の PC からのアクセスだけを受け付けます。

- `127.0.0.1` だけで待ち受け、さらに接続元がループバック以外なら拒否
- **DNS リバインディング対策**: `Host` ヘッダーが `127.0.0.1` / `localhost` / `[::1]` と設定したポートの組み合わせ以外なら拒否
- **CSRF 対策**: POST / DELETE などは `Origin` と `Sec-Fetch-Site` を確認し、他サイトからのリクエストを拒否
- `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`、`Cross-Origin-Resource-Policy: same-origin` を付与

ブラウザ以外（curl など）からのローカルアクセスは許可。
