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
        "win32gui",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PIL",
        "pytest",
        # 桌面路径改用 ctypes 调 shell32，不再需要 win32com.shell。
        # 排除 win32com.shell/win32ui 可去掉 mfc140u.dll(约 5.6MB) 依赖，
        # 既显著减小体积，又让纯内网 Win10/11（未装 VC++ 运行库）也能直接运行。
        "win32com.shell",
        "win32ui",
        # 内网工具，无联网/TLS 需求：排除 ssl 与 openssl 扩展，
        # 可直接去掉 libssl-3.dll(~0.8MB) 与 libcrypto-3.dll(~5.2MB)。
        # hashlib 保留但走 CPython 内置 _sha2（random 仍能取到 sha512），
        # 因此排除 _hashlib 扩展不会破坏功能，只去掉对 libcrypto 的依赖。
        "ssl",
        "_ssl",
        "_hashlib",
        # 未被使用、且会牵连 socket/网络栈或较大 stdlib 的模块
        "socket",
        "_socket",
        "select",
        "asyncio",
        "multiprocessing",
        "unittest",
        "pydoc",
        "doctest",
        "pdb",
        "profile",
        "cProfile",
        "difflib",
        "getpass",
        "calendar",
        "argparse",
        "optparse",
        "tkinter.dnd",
        "tkinter.tix",
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
