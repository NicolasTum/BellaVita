# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path.cwd()

block_cipher = None

a = Analysis(
    ["app/main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        ("assets", "assets"),
    ],
    hiddenimports=[
        "argon2",
        "argon2.low_level",
        "passlib.handlers.argon2",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        ".env",
        "backups",
        "build",
        "data",
        "dist",
        "exports",
        "logs",
        "pytest",
        "tests",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Club de Compras",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
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
    name="Club de Compras",
)

app = BUNDLE(
    coll,
    name="Club de Compras.app",
    icon="assets/icons/app_icon.icns",
    bundle_identifier="com.clubcompras.desktop",
    info_plist={
        "CFBundleName": "Club de Compras",
        "CFBundleDisplayName": "Club de Compras",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
    },
)
