# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


version_values = {}
exec(
    compile(
        Path("version.py").read_text(encoding="utf-8"),
        "version.py",
        "exec",
    ),
    version_values,
)
artifact_name = (
    f"{version_values['APP_NAME']}_{version_values['VERSION_TAG']}"
)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets/mouse_gesture.ico", "assets")],
    hiddenimports=[
        "pythoncom",
        "pywintypes",
        "win32com.client",
        "win32com.shell.shell",
        "win32com.shell.shellcon",
        "win32gui",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PIL",
        "pytest",
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=artifact_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["assets/mouse_gesture.ico"],
    version="version_info.txt",
)
