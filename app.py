"""Local image search server. Run: python app.py  ->  http://127.0.0.1:5055"""
import json
import re
import subprocess
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from common import (CONCEPT_WEIGHT, CONCEPTS_FILE, DEVICE, PORT, RES_DIR, THUMB_DIR, load_config,
                    load_model, save_config)
from index import build_index, load_existing

STATIC_DIR = RES_DIR / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR))
model, preprocess, tokenizer = load_model()
state = {}
job = {"running": False, "log": [], "error": None}
job_lock = threading.Lock()
concepts = {}  # label -> {"paths": [example image paths]}
concept_lock = threading.Lock()


def load_index():
    roots = load_config()["roots"]
    meta, emb = load_existing()
    if emb is None:
        meta, emb = [], np.zeros((0, 1024), np.float32)
    # hide images of folders that were removed from the config but not yet reindexed
    keep = [i for i, m in enumerate(meta) if m["root"] in roots]
    meta = [meta[i] for i in keep]
    emb = emb[keep]
    ridx = {r: n for n, r in enumerate(roots)}
    rootkey = np.array([f"r{ridx[m['root']]}" for m in meta], dtype=object)
    subkey = np.array([f"r{ridx[m['root']]}/{m['rel'].split('/')[0]}" if "/" in m["rel"] else ""
                       for m in meta], dtype=object)
    # folder that directly contains each image, e.g. "r0" or "r0/arts/sketch"
    dirkey = np.array([f"r{ridx[m['root']]}/{m['rel'].rsplit('/', 1)[0]}" if "/" in m["rel"]
                       else f"r{ridx[m['root']]}" for m in meta], dtype=object)
    state.update(meta=meta, emb=torch.from_numpy(np.ascontiguousarray(emb)).to(DEVICE),
                 rootkey=rootkey, subkey=subkey, dirkey=dirkey, roots=roots,
                 pidx={m["path"]: i for i, m in enumerate(meta)})
    text_vec.cache_clear()
    print(f"loaded {len(meta)} images from {len(roots)} folders")


def folder_mask(folder):
    """Boolean numpy mask of images inside the filter (None = all)."""
    if not folder:
        return None
    return (state["rootkey"] == folder) | (state["subkey"] == folder)


def item(i, score=None):
    m = state["meta"][i]
    d = {"id": int(i), "rel": m["rel"], "root": m["root"], "dir": state["dirkey"][i],
         "w": m["w"], "h": m["h"]}
    if score is not None:
        d["score"] = round(float(score), 4)
    return d


def page_args():
    offset = max(int(request.args.get("offset", 0)), 0)
    limit = min(max(int(request.args.get("limit", 60)), 1), 500)
    return offset, limit


def rank(scores, folder, exclude=None):
    """Return results page [offset, offset+limit) ranked by score (one per image)."""
    offset, limit = page_args()
    if not len(state["meta"]):
        return {"results": [], "has_more": False}
    scores = scores.clone()
    mask = folder_mask(folder)
    if mask is not None:
        scores = scores.masked_fill(torch.from_numpy(~mask).to(DEVICE), -2)
    if exclude is not None:
        scores[exclude] = -2
    top = torch.topk(scores, min(offset + limit + 1, len(scores)))
    vals, idx = top.values.tolist(), top.indices.tolist()
    valid = [(s, i) for s, i in zip(vals, idx) if s > -1.5]
    page = valid[offset:offset + limit]
    return {"results": [item(i, s) for s, i in page], "has_more": len(valid) > offset + limit}


@lru_cache(maxsize=64)
def text_vec(q):
    with torch.no_grad():
        t = model.encode_text(tokenizer([q]).to(DEVICE))[0].float()
    return t / t.norm()


# ---------- labels (stored as "concepts") ----------

def load_concepts():
    if CONCEPTS_FILE.exists():
        concepts.update(json.loads(CONCEPTS_FILE.read_text(encoding="utf-8")))


def save_concepts():
    CONCEPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONCEPTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(concepts, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(CONCEPTS_FILE)


def concept_ids(name):
    """Index positions of a concept's example images that are currently indexed."""
    pidx = state["pidx"]
    return [pidx[p] for p in concepts[name]["paths"] if p in pidx]


def find_name(name):
    """Existing concept key matching name case-insensitively, or None."""
    low = name.lower()
    return next((k for k in concepts if k.lower() == low), None)


def zscore(s):
    return (s - s.mean()) / (s.std() + 1e-6)


def search_scores(q):
    """Scores for a text query. Registered labels in q are replaced by the mean
    vector of their example images; the remaining words go through the CLIP text
    encoder. Mixed queries fuse the two (z-scored) with CONCEPT_WEIGHT."""
    with concept_lock:
        known = {n: concept_ids(n) for n in concepts}
    known = {n: ids for n, ids in known.items() if ids}
    hits, rest = [], q
    if known:
        pat = re.compile("|".join(re.escape(n) for n in sorted(known, key=len, reverse=True)), re.I)
        lower = {n.lower(): n for n in known}
        hits = list(dict.fromkeys(lower[m.group(0).lower()] for m in pat.finditer(q)))
        rest = pat.sub(" ", q)
    if not hits:
        return state["emb"] @ text_vec(q), []
    rest = re.sub(r"[\s、。,，・/]+", " ", rest).strip()
    vecs = []
    for n in hits:
        v = state["emb"][known[n]].mean(0)
        vecs.append(v / v.norm())
    c = torch.stack(vecs).mean(0)
    scores = state["emb"] @ (c / c.norm())
    if rest:
        scores = CONCEPT_WEIGHT * zscore(scores) + (1 - CONCEPT_WEIGHT) * zscore(state["emb"] @ text_vec(rest))
    return scores, [{"name": n, "count": len(known[n])} for n in hits]


def clean_name(n):
    return " ".join(str(n or "").split())[:60]


def concepts_json():
    with concept_lock:
        out = [{"name": n, "ids": concept_ids(n), "total": len(c["paths"])} for n, c in concepts.items()]
    out.sort(key=lambda c: c["name"].lower())
    return jsonify(concepts=out)


@app.get("/api/concepts")
def list_concepts():
    return concepts_json()


@app.post("/api/concepts/add")
def concept_add():
    d = request.json or {}
    name = clean_name(d.get("name"))
    if not name:
        return jsonify(error="ラベル名を入力してください"), 400
    ids = d["ids"] if isinstance(d.get("ids"), list) else [d.get("id", -1)]
    new = [get_meta(int(i))["path"] for i in ids]
    if not new:
        return jsonify(error="画像が選択されていません"), 400
    with concept_lock:
        paths = concepts.setdefault(find_name(name) or name, {"paths": []})["paths"]
        paths += [p for p in dict.fromkeys(new) if p not in paths]
        save_concepts()
    return concepts_json()


@app.post("/api/concepts/remove")
def concept_remove():
    d = request.json or {}
    path = get_meta(int(d.get("id", -1)))["path"]
    with concept_lock:
        key = find_name(clean_name(d.get("name")))
        if key:
            paths = concepts[key]["paths"]
            if path in paths:
                paths.remove(path)
            if not paths:
                del concepts[key]
            save_concepts()
    return concepts_json()


@app.post("/api/concepts/rename")
def concept_rename():
    d = request.json or {}
    new = clean_name(d.get("new"))
    if not new:
        return jsonify(error="ラベル名を入力してください"), 400
    with concept_lock:
        key = find_name(clean_name(d.get("name")))
        if not key:
            abort(404)
        paths = concepts.pop(key)["paths"]
        other = find_name(new)
        if other:  # merge into an existing name
            concepts[other]["paths"] += [p for p in paths if p not in concepts[other]["paths"]]
        else:
            concepts[new] = {"paths": paths}
        save_concepts()
    return concepts_json()


@app.post("/api/concepts/delete")
def concept_delete():
    with concept_lock:
        key = find_name(clean_name((request.json or {}).get("name")))
        if key:
            del concepts[key]
            save_concepts()
    return concepts_json()


def get_meta(i):
    if not 0 <= i < len(state["meta"]):
        abort(404)
    return state["meta"][i]


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/info")
def info():
    roots = []
    for n, r in enumerate(state["roots"]):
        mask = state["rootkey"] == f"r{n}"
        subs = sorted({s.split("/", 1)[1] for s in state["subkey"][mask] if s})
        roots.append({"key": f"r{n}", "path": r, "name": Path(r).name or r,
                      "count": int(mask.sum()), "subs": subs})
    return jsonify(count=len(state["meta"]), roots=roots)


@app.get("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify(results=[], has_more=False)
    if not len(state["meta"]):
        return jsonify(results=[], has_more=False)
    scores, matched = search_scores(q)
    return jsonify(concepts=matched, **rank(scores, request.args.get("folder")))


@app.get("/api/similar/<int:i>")
def similar(i):
    get_meta(i)
    return jsonify(query=item(i), **rank(state["emb"] @ state["emb"][i], request.args.get("folder"), exclude=i))


def paged(ids):
    offset, limit = page_args()
    return {"results": [item(i) for i in ids[offset:offset + limit]],
            "has_more": len(ids) > offset + limit, "total": int(len(ids))}


@app.get("/api/random")
def random_items():
    seed = int(request.args.get("seed", 0))
    ids = np.arange(len(state["meta"]))
    mask = folder_mask(request.args.get("folder"))
    if mask is not None:
        ids = ids[mask]
    return jsonify(paged(np.random.default_rng(seed).permutation(ids)))


@app.get("/api/browse")
def browse():
    """Images directly inside one folder (dir = 'r0' or 'r0/sub/dir'), sorted by name."""
    d = request.args.get("dir", "")
    ids = np.flatnonzero(state["dirkey"] == d)
    ids = sorted(ids, key=lambda i: state["meta"][i]["rel"].lower())
    return jsonify(paged(ids))


@app.get("/api/tree")
def tree():
    """Nested folder tree per root with direct (count) and recursive (total) image counts."""
    out = []
    for n, r in enumerate(state["roots"]):
        node = {"key": f"r{n}", "name": r, "count": 0, "total": 0, "children": {}}
        for m in (state["meta"][i] for i in np.flatnonzero(state["rootkey"] == f"r{n}")):
            parts = m["rel"].split("/")[:-1]
            cur = node
            cur["total"] += 1
            for p in parts:
                cur = cur["children"].setdefault(
                    p, {"key": f"{cur['key']}/{p}", "name": p, "count": 0, "total": 0, "children": {}})
                cur["total"] += 1
            cur["count"] += 1
        out.append(node)

    def finish(nd):
        nd["children"] = [finish(c) for c in sorted(nd["children"].values(), key=lambda c: c["name"].lower())]
        return nd
    return jsonify(roots=[finish(nd) for nd in out])


@app.get("/thumb/<int:i>")
def thumb(i):
    return send_from_directory(THUMB_DIR, get_meta(i)["thumb"], max_age=86400)


@app.get("/image/<int:i>")
def image(i):
    return send_file(get_meta(i)["path"], max_age=3600)


@app.post("/api/reveal/<int:i>")
def reveal(i):
    subprocess.Popen(["explorer", "/select,", get_meta(i)["path"]])
    return jsonify(ok=True)


# ---------- folder management ----------

@app.post("/api/roots")
def add_root():
    raw = (request.json or {}).get("path", "").strip().strip('"')
    if not raw:
        return jsonify(error="パスを入力してください"), 400
    p = Path(raw)
    if not p.is_dir():
        return jsonify(error=f"フォルダが見つかりません: {raw}"), 400
    path = str(p.resolve()) if not raw.startswith("\\\\") else str(p)
    cfg = load_config()
    for r in cfg["roots"]:
        a, b = path.lower().rstrip("\\") + "\\", r.lower().rstrip("\\") + "\\"
        if a == b:
            return jsonify(error="既に登録されています"), 400
        if a.startswith(b) or b.startswith(a):
            return jsonify(error=f"登録済みフォルダと重なっています: {r}"), 400
    cfg["roots"].append(path)
    save_config(cfg)
    start_reindex()
    return jsonify(roots=cfg["roots"])


@app.delete("/api/roots/<int:n>")
def remove_root(n):
    cfg = load_config()
    if not 0 <= n < len(cfg["roots"]):
        abort(404)
    cfg["roots"].pop(n)
    save_config(cfg)
    start_reindex()
    return jsonify(roots=cfg["roots"])


def start_reindex():
    with job_lock:
        if job["running"]:
            job["pending"] = True  # run once more after the current pass
            return False
        job.update(running=True, log=[], error=None, pending=False)
    threading.Thread(target=reindex_worker, daemon=True).start()
    return True


def reindex_worker():
    while True:
        try:
            build_index(load_config()["roots"], model, preprocess,
                        log=lambda s: (job["log"].append(s), print(s)))
            load_index()
        except Exception as e:
            job["error"] = str(e)
            print("reindex failed:", e)
        with job_lock:
            if not job.get("pending"):
                job["running"] = False
                return
            job["pending"] = False


@app.post("/api/reindex")
def reindex():
    start_reindex()
    return jsonify(ok=True)


@app.get("/api/reindex")
def reindex_status():
    return jsonify(running=job["running"], log=job["log"][-8:], error=job["error"])


def serve(on_ready=None):
    import logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # hide per-request access logs
    load_index()
    load_concepts()
    print(f"画像検索サーバー起動完了: http://127.0.0.1:{PORT}", flush=True)
    if on_ready:
        on_ready()
    app.run(host="127.0.0.1", port=PORT, threaded=True)


if __name__ == "__main__":
    serve()
