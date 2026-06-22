# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH)
IS_MAC = sys.platform == "darwin"
ICON = ROOT / "assets" / ("Yingcun.icns" if IS_MAC else "Yingcun.ico")

datas = [(str(ROOT / "web"), "web")]
datas += collect_data_files("yt_dlp")

a = Analysis(
    [str(ROOT / "web_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "pytest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Yingcun",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ICON),
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Yingcun",
)

if IS_MAC:
    app = BUNDLE(
        collection,
        name="Yingcun.app",
        icon=str(ICON),
        bundle_identifier="com.codebluefriend.yingcun",
        info_plist={
            "CFBundleDisplayName": "映存",
            "CFBundleName": "Yingcun",
            "CFBundleShortVersionString": "0.3.0",
            "CFBundleVersion": "0.3.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
