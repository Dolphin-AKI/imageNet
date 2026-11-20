# image-search

多言語 CLIP を使ったローカル画像検索ツール。
指定フォルダ内の画像をインデックス化し、日本語を含むテキストや類似画像でブラウザから検索できます。

## クイックスタート

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu130
start.bat
```

ブラウザで http://127.0.0.1:5055 が開いたら、画面から検索したいフォルダを追加します。
初回はモデル（約 5GB）がダウンロードされます。

## ドキュメント

- [セットアップと設定](docs/setup.md)
- [配布方法（ポータブル版 / フルパッケージ exe 版）](docs/distribution.md)
- [構成](docs/architecture.md)

## ライセンス

[MIT](LICENSE)

利用するモデル（open_clip / LAION）やライブラリ、ポータブル版に同梱する uv は、それぞれのライセンスに従います。
