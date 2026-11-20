"""Launcher (entry point for the exe).

    ImageSearch.exe               start server and open the browser
    ImageSearch.exe --reindex     update the index first, then start
    ImageSearch.exe --index-only  update the index and exit (add --full to rebuild)
    ImageSearch.exe --no-browser  do not open the browser
"""
import sys
import threading
import traceback
import urllib.request
import webbrowser


def main():
    args = sys.argv[1:]
    # common reads settings.json and sets the model cache env before torch is imported
    from common import DATA_DIR, MODEL_DIR, PORT, SETTINGS_FILE, load_config
    url = f"http://127.0.0.1:{PORT}"

    if "--index-only" not in args:
        try:  # already running -> just open the browser
            urllib.request.urlopen(url + "/api/info", timeout=2)
            print("画像検索サーバーは既に起動しています。ブラウザを開きます。")
            webbrowser.open(url)
            return
        except Exception:
            pass

    print(f"設定ファイル : {SETTINGS_FILE}")
    print(f"データ       : {DATA_DIR}")
    print(f"モデル       : {MODEL_DIR or '(既定の HuggingFace キャッシュ)'}")

    if "--reindex" in args or "--index-only" in args:
        from index import build_index
        print("インデックスを更新しています...")
        build_index(load_config()["roots"], full="--full" in args)
        if "--index-only" in args:
            return

    print("画像検索サーバーを起動しています（モデル読み込みに20-30秒かかります）...")
    print("終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。\n")
    import app
    on_ready = None
    if "--no-browser" not in args:
        on_ready = lambda: threading.Timer(1.0, webbrowser.open, (url,)).start()
    app.serve(on_ready)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        if getattr(sys, "frozen", False):
            input("\nエラーが発生しました。Enter キーで終了します...")
        sys.exit(1)
