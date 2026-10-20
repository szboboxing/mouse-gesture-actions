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
    datas=[
        ("assets/mouse_gesture.ico", "assets"),
        # 轮盘风格壁纸（奶油 / 冷淡 / 苹果 × 明暗 2 模式，共 6 张 PNG，约 0.19MB）
        ("assets/wallpapers", "assets/wallpapers"),
        # 立体图标表（奶油 / 苹果 × 明暗 × 9 图标 × 4 尺寸，共 144 张，约 0.22MB）
        # Pillow 不参与打包，所以这些图必须离线预渲染好随包带上。
        ("assets/icons", "assets/icons"),
    ],
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
        # ---- V2.7.2 体积裁剪：逐项确认过引用来源，均可安全排除 ----
        # random 只在库内的 _test_generator()（CPython 自测函数，永远不会被调用）
        # 里 import statistics，statistics 再牵连 decimal / fractions / _pydecimal
        # 以及 _decimal.pyd，合计约 0.2MB。排除后 random.random()/choice() 照常可用。
        "statistics",
        "decimal",
        "_decimal",
        "fractions",
        "_pydecimal",
        # 浏览器磁贴改为直接 os.startfile()（等价于 webbrowser 在 Windows 上的
        # 最终调用），webbrowser 及其 subprocess / signal / selectors / shlex
        # 依赖链整条下线；同时排除以防被其它模块悄悄带回。
        "webbrowser",
        "subprocess",
        "signal",
        "selectors",
        "shlex",
        # shutil / zipfile 对下面这几个都是 try/except ImportError 的可选压缩后端，
        # 本程序不解压任何归档，排除后 _lzma.pyd 与 _bz2.pyd 不再进包。
        "lzma",
        "_lzma",
        "bz2",
        "_bz2",
        "tarfile",
        "gzip",
        "_compression",
        # 只有 importlib.metadata 会用到 email 与 csv，而 importlib.metadata 在本
        # 程序里没有任何调用点（唯一引用它的是 makepy，同样未被使用）。
        # 少一个 SMTP/HTTP 报文解析库，也更符合内网无外联的安全要求。
        "importlib.metadata",
        "email",
        "csv",
    ],
    noarchive=False,
    optimize=2,
)

# ---- Tcl / Tk 运行时里用不到的可选包 ----
# PyInstaller 收集 Tcl/Tk 时没有可配置项（hooksconfig 不支持），只能在 Analysis
# 结束后按目标路径过滤。下面几项都核对过 Tcl 的 package require 关系：
#   tzdata     —— Tcl 的 clock 在 Windows 上读注册表时区，不查 zoneinfo 文件
#   http       —— 内网工具不做任何 HTTP 请求（去掉后也没有外联能力）
#   tcltest    —— 只有 Tk 自带的控制台/自检脚本会 require，运行时用不到
#   platform   —— 无人 require，仅被 Tcl 测试框架使用
# 必须保留：msgcat（clock.tcl 与 tk.tcl 都 require）、opt0.4（被 require）、
# encoding/（中文 Windows 的 cp936 等系统编码）、msgs/（本地化按钮文案）。
_PRUNED_TCL_PREFIXES = (
    "_tcl_data/tzdata/",
    "_tcl_data/http1.0/",
    "tcl8/8.6/http",
    "tcl8/8.5/tcltest",
    "tcl8/8.4/platform",
)


def _keep_datas(entry):
    name = str(entry[0]).replace("\\", "/")
    return not any(name.startswith(prefix) for prefix in _PRUNED_TCL_PREFIXES)


_pruned = [entry for entry in a.datas if not _keep_datas(entry)]
a.datas[:] = [entry for entry in a.datas if _keep_datas(entry)]
print(f"[spec] 剔除 Tcl/Tk 可选包 {len(_pruned)} 个文件")

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
