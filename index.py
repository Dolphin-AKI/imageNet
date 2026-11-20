"""Build / incrementally update the image embedding index for all folders in config.json.

CLI usage: python index.py [--full]
Only new or modified files are embedded; files that were deleted, or that belong
to folders removed from the config, are dropped.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

from common import (DATA_DIR, DEVICE, EMB_FILE, IMAGE_EXTS, META_FILE, THUMB_DIR,
                    load_config, load_model)

BATCH = 16
THUMB_SIZE = 320


def thumb_name(path: str) -> str:
    return hashlib.sha1(path.encode("utf-8")).hexdigest() + ".jpg"


def open_rgb(path):
    img = Image.open(path)
    img.seek(0)  # first frame for gif/webp
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def load_existing():
    if not (META_FILE.exists() and EMB_FILE.exists()):
        return [], None
    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    if any("path" not in m for m in meta):  # pre multi-folder index: rebuild from scratch
        return [], None
    return meta, np.load(EMB_FILE)


def build_index(roots, model=None, preprocess=None, full=False, log=print):
    """Scan roots, embed new/changed images, save the index. Returns image count."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(exist_ok=True)

    old_meta, old_emb = ([], None) if full else load_existing()
    old_by_path = {m["path"]: (i, m) for i, m in enumerate(old_meta)}

    files = []
    for root in roots:
        rp = Path(root)
        if not rp.is_dir():
            log(f"フォルダが見つかりません: {root}")
            continue
        found = sorted(p for p in rp.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
        log(f"{root}: {len(found)} 枚")
        files += [(p, root) for p in found]

    keep_meta, keep_vecs, todo = [], [], []
    for p, root in files:
        path = str(p)
        st = p.stat()
        prev = old_by_path.get(path)
        if prev and prev[1]["mtime"] == st.st_mtime and prev[1]["size"] == st.st_size:
            m = dict(prev[1], root=root, rel=p.relative_to(root).as_posix())
            keep_meta.append(m)
            keep_vecs.append(old_emb[prev[0]])
        else:
            todo.append((p, root, st))
    log(f"再利用 {len(keep_meta)} 枚 / 新規・更新 {len(todo)} 枚")

    new_meta, new_vecs = [], []
    if todo:
        if model is None:
            model, preprocess, _ = load_model()
        dtype = torch.float16 if DEVICE == "cuda" else torch.float32
        batch_imgs, batch_info = [], []

        def flush():
            if not batch_imgs:
                return
            x = torch.stack(batch_imgs).to(DEVICE, dtype=dtype)
            with torch.no_grad():
                v = model.encode_image(x)
                v = v / v.norm(dim=-1, keepdim=True)
            new_vecs.extend(v.float().cpu().numpy())
            new_meta.extend(batch_info)
            batch_imgs.clear()
            batch_info.clear()

        for n, (p, root, st) in enumerate(todo, 1):
            try:
                img = open_rgb(p)
            except Exception as e:  # corrupt / unsupported file
                log(f"スキップ {p}: {e}")
                continue
            t = img.copy()
            t.thumbnail((THUMB_SIZE, THUMB_SIZE))
            tn = thumb_name(str(p))
            t.save(THUMB_DIR / tn, "JPEG", quality=85)
            batch_imgs.append(preprocess(img))
            batch_info.append({"path": str(p), "root": root, "rel": p.relative_to(root).as_posix(),
                               "mtime": st.st_mtime, "size": st.st_size,
                               "w": img.width, "h": img.height, "thumb": tn})
            if len(batch_imgs) >= BATCH:
                flush()
                log(f"埋め込み中 {n}/{len(todo)}")
        flush()

    meta = keep_meta + new_meta
    vecs = np.stack(keep_vecs + new_vecs).astype(np.float32) if meta else np.zeros((0, 1024), np.float32)
    np.save(EMB_FILE, vecs)
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    used = {m["thumb"] for m in meta}  # drop thumbnails of removed images
    for f in THUMB_DIR.glob("*.jpg"):
        if f.name not in used:
            f.unlink()
    log(f"完了: {len(meta)} 枚")
    return len(meta)


if __name__ == "__main__":
    build_index(load_config()["roots"], full="--full" in sys.argv)
