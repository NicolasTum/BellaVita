# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path.cwd()
version_namespace = {}
exec((project_dir / "app" / "version.py").read_text(encoding="utf-8"), version_namespace)
app_version = version_namespace["VERSION"]
version_tuple = tuple(int(part) for part in app_version.split(".")) + (0,)
version_info_path = project_dir / "build" / "windows_version_info.txt"
version_info_path.parent.mkdir(parents=True, exist_ok=True)
version_info_path.write_text(
    f"""
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Bella Vita'),
          StringStruct('FileDescription', 'Bella Vita - Club de Compras'),
          StringStruct('FileVersion', '{app_version}'),
          StringStruct('InternalName', 'Club de Compras'),
          StringStruct('OriginalFilename', 'Club de Compras.exe'),
          StringStruct('ProductName', 'Bella Vita - Club de Compras'),
          StringStruct('ProductVersion', '{app_version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""".strip(),
    encoding="utf-8",
)

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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icons/app_icon.ico",
    version=str(version_info_path),
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
