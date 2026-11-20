# PyInstaller spec.  Build:  .venv\Scripts\python.exe -m PyInstaller ImageSearch.spec --noconfirm
# Output: dist\ImageSearch\ImageSearch.exe (onedir; torch+CUDA is too large for onefile)
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

datas = [("static", "static")]
binaries = []
hiddenimports = []

for pkg in ("open_clip", "timm"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# torchvision loads its native ops (_C_stable.pyd) from its own package folder at runtime
import glob, os, torchvision
_tv = os.path.dirname(torchvision.__file__)
binaries += [(f, "torchvision") for ext in ("*.pyd", "*.dll") for f in glob.glob(os.path.join(_tv, ext))]

# transformers is lazily imported; only the XLM-R text tower is needed
hiddenimports += collect_submodules("transformers.models.xlm_roberta")
hiddenimports += ["transformers.models.auto", "ftfy", "regex", "tokenizers", "safetensors"]
datas += collect_data_files("transformers", include_py_files=False)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "tensorflow", "jax", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageSearch",
    console=True,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ImageSearch", upx=False)
