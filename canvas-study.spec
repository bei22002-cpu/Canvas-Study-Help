# canvas-study.spec  —  PyInstaller build spec for Canvas Study Help
# -----------------------------------------------------------------------
# Build:
#   pip install pyinstaller
#   pyinstaller canvas-study.spec
#
# Output lands in dist/CanvasStudyHelp  (folder) or dist/CanvasStudyHelp.exe
# -----------------------------------------------------------------------

import sys
from pathlib import Path

block_cipher = None

# Collect data files to bundle with the executable
datas = [
    ("canvas-app.html", "."),   # web UI
    ("canvas-proxy.py", "."),   # kept for reference / standalone use
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=["autostart"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CanvasStudyHelp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=True lets students see log messages; set False for a pure GUI app
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,   # macOS: set True if you need argv forwarding
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # replace with 'icon.ico' / 'icon.icns' when available
)

# macOS: wrap in .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="CanvasStudyHelp.app",
        icon=None,
        bundle_identifier="com.canvasstudyhelp.launcher",
        info_plist={
            "CFBundleName": "Canvas Study Help",
            "CFBundleDisplayName": "Canvas Study Help",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
