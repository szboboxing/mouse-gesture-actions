# 鼠标手势动作小工具

[![CI](https://github.com/szboboxing/mouse-gesture-actions/actions/workflows/ci.yml/badge.svg)](https://github.com/szboboxing/mouse-gesture-actions/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/szboboxing/mouse-gesture-actions?display_name=tag)](https://github.com/szboboxing/mouse-gesture-actions/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Windows 全局鼠标手势工具。按住鼠标右键绘制轨迹，松开后将手势转换为键盘组合键或系统动作；普通右键单击保持原有功能。

下载最新单文件版本：

<https://github.com/szboboxing/mouse-gesture-actions/releases/latest>

## 默认手势

| 手势 | 绘制方式 | 默认动作 |
|---|---|---|
| 左向圆圈 | 按住右键逆时针画圆 | `Ctrl+C` 复制 |
| 右向圆圈 | 按住右键顺时针画圆 | `Ctrl+V` 粘贴 |
| 对勾 | 先向右下，再向右上 | `Win+Shift+S` 截图 |
| 同向快划两次 | 快速向右上两次，或快速向左下两次 | 当前目录新建文件夹 |

快划必须方向相同，并在默认 850 毫秒间隔内完成。新建文件夹动作使用当前激活的文件资源管理器目录；在桌面执行时使用桌面目录。

## 使用方法

1. 运行 `鼠标手势动作小工具_V1.1.exe`。
2. 保持“正在监听”状态。
3. 按住鼠标右键画出完整轨迹。
4. 松开右键，动作立即执行，右下角显示识别结果。

界面可以修改复制、粘贴、截图对应的组合键，并配置：

- 识别灵敏度：灵敏、标准、稳健。
- 双划间隔：350-1500 毫秒。
- 启动后自动监听。
- 启动时最小化。

## V1.1 界面工具

- 鼠标统计器：统计本次运行的左键、右键次数、鼠标移动像素距离及各功能成功使用次数。
- 快捷启动：计算器、系统默认浏览器和 Windows 媒体播放器。
- 显示调节：亮度上下调节与对比度上下调节，每次调整约 5%。
- 自定义按钮：两个按钮均可右键编辑名称，并设置要打开的程序、文件、文件夹或网址。
- 随机鼓励语：启动时随机显示一句，也可单击“换一句”刷新。

内置屏幕亮度优先使用 Windows WMI；外接显示器亮度和对比度使用 DDC/CI。显示器不支持或未启用 DDC/CI 时，软件会显示失败原因，不会修改其他系统设置。

设置保存在：

```text
%APPDATA%\MouseGestureActions\settings.json
```

## 快捷键格式

使用加号连接按键，例如：

```text
Ctrl+C
Ctrl+Shift+A
Win+Shift+S
Alt+F4
```

支持 `Ctrl`、`Shift`、`Alt`、`Win`、字母、数字、`F1-F24` 及常见导航键。

## 当前目录规则

“同向快划两次”仅在以下位置新建文件夹：

- 当前激活的 Windows 文件资源管理器窗口。
- Windows 桌面。

如果当前前台程序不是资源管理器或桌面，程序会提示先激活资源管理器，不会在错误位置创建文件夹。重名时依次使用：

```text
新建文件夹
新建文件夹 (2)
新建文件夹 (3)
```

## 版本与发布规则

- 版本从 `V1.0` 开始，后续依次递增为 `V1.1`、`V1.2`。
- 唯一版本来源是 `version.py` 中的 `APP_VERSION`。
- Git 标签与 GitHub Release 使用相同的 `Vx.y` 名称。
- 每次构建会自动清理 `dist`，本地只保留版本号最高的两个 EXE。
- 本地 EXE 使用中文产品名，GitHub Release 使用稳定下载名 `mouse-gesture-actions-Vx.y.exe`。
- GitHub Release 永久保留已发布版本，不受本地清理规则影响。

发布新版本时：

1. 修改 `version.py` 中的 `APP_VERSION`。
2. 更新功能和测试。
3. 运行 `.\build.ps1`。
4. 提交代码并推送同名版本标签，例如 `V1.1`。

GitHub Actions 会校验标签与代码版本一致，并自动创建 Release、上传单文件 EXE。

## 开源许可

本项目采用 [MIT License](LICENSE)，允许学习、修改、分发和商业使用，但须保留原许可证和版权声明。

## 开发与测试

环境要求：

- Windows 10/11
- Python 3.11+

安装依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

运行源码：

```powershell
python main.py
```

运行测试：

```powershell
python -m unittest discover -s tests -v
```

构建单文件 EXE：

```powershell
.\build.ps1
```

构建产物：

```text
dist\鼠标手势动作小工具_V1.1.exe
```

## 权限说明

Windows 会阻止普通权限程序向管理员权限窗口发送按键。如果目标程序以管理员身份运行，请同时以管理员身份运行本工具。

监听开启时，明显的右键拖动会被视为手势，因此需要使用应用本身的“右键拖动”功能时，应先暂停手势监听。
