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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Club de Compras",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
