# PyInstaller : `pyinstaller packaging/ew_to_obs.spec --clean -y` (depuis la racine du dépôt).
# --onedir (et non --onefile) : démarrage plus rapide, moins de faux positifs d'antivirus.
import sys

from PyInstaller.utils.hooks import collect_data_files

windowed = sys.platform in ("win32", "darwin")  # pas de console noire ; Linux : lancé du terminal

a = Analysis(
    ["launcher.py"],
    pathex=["../src"],
    datas=collect_data_files("ew_to_obs"),  # la page web (public/) à côté du code
    hiddenimports=["tkinter"],
    excludes=["playwright", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ew_to_obs",
    console=not windowed,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ew_to_obs")
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Easyworship vers OBS.app",
        bundle_identifier="io.github.vgiudicelli1.ew-to-obs",
        info_plist={"NSHighResolutionCapable": True},
    )
