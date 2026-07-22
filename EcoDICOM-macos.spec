# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller para macOS → EcoDICOM.app"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    "app",
    "app.ui.main_window",
    "app.dicom.generator",
    "app.device.capture",
    "app.device.detector",
    "app.storage.database",
]

for pkg in ("PySide6", "pydicom"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="EcoDICOM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EcoDICOM",
)

app = BUNDLE(
    coll,
    name="EcoDICOM.app",
    icon=None,
    bundle_identifier="com.ecodicom.app",
    info_plist={
        "CFBundleName": "EcoDICOM",
        "CFBundleDisplayName": "EcoDICOM",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
        "NSCameraUsageDescription": (
            "EcoDICOM necesita acceso a la cámara o capturadora "
            "para obtener imágenes del ecógrafo."
        ),
        "NSMicrophoneUsageDescription": (
            "Algunos dispositivos de captura de video requieren acceso al micrófono."
        ),
    },
)
