"""Shared settings and model loading.

settings.json (next to app.py / the exe) controls where data and models live:
    {
      "data_dir": "data",     # index, thumbnails (relative = relative to the app folder)
      "model_dir": "",        # HuggingFace model cache; "" = default (~/.cache/huggingface/hub)
      "port": 5055,
      "concept_weight": 0.6   # label vs. remaining words when a query mixes both (0-1)
    }
"""
import json
import os
import sys
from pathlib import Path

# --- paths -----------------------------------------------------------------
FROZEN = getattr(sys, "frozen", False)
# folder holding settings.json / config.json / data (next to the exe when frozen)
APP_DIR = Path(sys.executable).parent if FROZEN else Path(__file__).parent
# bundled read-only resources (static/)
RES_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))

SETTINGS_FILE = APP_DIR / "settings.json"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_SETTINGS = {"data_dir": "data", "model_dir": "", "port": 5055, "concept_weight": 0.6}


def load_settings():
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig")))
    else:
        SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s


def _resolve(p):
    p = Path(os.path.expandvars(os.path.expanduser(str(p))))
    return p if p.is_absolute() else APP_DIR / p


SETTINGS = load_settings()
DATA_DIR = _resolve(SETTINGS["data_dir"] or "data")
MODEL_DIR = _resolve(SETTINGS["model_dir"]) if SETTINGS.get("model_dir") else None
PORT = int(SETTINGS.get("port") or 5055)
CONCEPT_WEIGHT = min(max(float(SETTINGS.get("concept_weight", 0.6)), 0.0), 1.0)

THUMB_DIR = DATA_DIR / "thumbs"
EMB_FILE = DATA_DIR / "embeddings.npy"
META_FILE = DATA_DIR / "meta.json"
CONCEPTS_FILE = DATA_DIR / "concepts.json"  # labels -> example image paths

# must be set before huggingface_hub / transformers / open_clip are imported
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
if MODEL_DIR:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_CACHE"] = str(MODEL_DIR)
    os.environ["TORCH_HOME"] = str(MODEL_DIR / "torch")

import torch  # noqa: E402
import open_clip  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}

# Multilingual CLIP (Japanese text queries work)
MODEL_NAME = "xlm-roberta-large-ViT-H-14"
PRETRAINED = "frozen_laion5b_s13b_b90k"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    cfg = {"roots": []}  # add folders from the web UI or edit config.json
    save_config(cfg)
    return cfg


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_model():
    cache = str(MODEL_DIR) if MODEL_DIR else None
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED, cache_dir=cache)
    model = model.to(DEVICE).eval()
    if DEVICE == "cuda":
        model = model.half()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME, cache_dir=cache)
    return model, preprocess, tokenizer
