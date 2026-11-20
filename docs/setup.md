# セットアップと設定

## 必要環境

- Windows
- Python 3.10
- NVIDIA GPU 推奨（無くても CPU で動作しますが遅くなります）
- モデル用に約 5GB、ライブラリ用に約 3GB の空き容量

## インストール

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu130
```

uv を使う場合は、GPU とドライバに合った PyTorch が自動で選ばれます。

```powershell
uv venv --python 3.10 .venv
uv pip install --torch-backend=auto -r requirements.txt
```

## 設定ファイル

どちらも無ければ初回起動時に既定値で自動生成されます。雛形は `*.example.json` にあります。

### config.json

インデックス対象のフォルダ一覧です。ブラウザの画面からも追加・削除できます。

```json
{
  "roots": ["D:/path/to/images", "\\\\SERVER\\share\\images"]
}
```

### settings.json

| キー | 既定値 | 内容 |
|---|---|---|
| `data_dir` | `"data"` | インデックス・サムネイルの保存先（相対パスはアプリのフォルダ基準） |
| `model_dir` | `""` | モデルの保存先。空なら HuggingFace の既定キャッシュ（`~/.cache/huggingface/hub`） |
| `port` | `5055` | サーバーのポート |
| `concept_weight` | `0.6` | 検索語にラベルと通常の語が混ざるときの、ラベル側の重み（0〜1） |

## 使い方

```powershell
start.bat                 # サーバー起動 + ブラウザを開く
start.bat /reindex        # 先に差分インデックス更新してから起動
python index.py           # インデックスの差分更新のみ
python index.py --full    # インデックスを作り直す
```

`main.py`（exe 版・ポータブル版のエントリーポイント）のオプション:

| オプション | 内容 |
|---|---|
| `--reindex` | 先にインデックスを更新してから起動 |
| `--index-only` | インデックスを更新して終了（`--full` で作り直し） |
| `--no-browser` | ブラウザを開かない |

既にサーバーが起動している場合は、ブラウザを開くだけで終了します。
