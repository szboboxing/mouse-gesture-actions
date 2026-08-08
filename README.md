# 鼠标手势动作小工具

[![CI](https://github.com/szboboxing/mouse-gesture-actions/actions/workflows/ci.yml/badge.svg)](https://github.com/szboboxing/mouse-gesture-actions/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/szboboxing/mouse-gesture-actions?display_name=tag)](https://github.com/szboboxing/mouse-gesture-actions/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Windows 全局鼠标组合工具。按住鼠标右键时，滚轮和侧键可执行复制、增强粘贴及截图；普通侧键还可分别映射为自定义键盘快捷键。未启用映射的侧键保持浏览器前进、后退原生功能。

左侧“鼠标按键测试”模块可实时检测左键、右键、中键、滚轮方向及两枚侧键，并可重新确认、保存实际可用的截图侧键。

下载最新单文件版本：

<https://github.com/szboboxing/mouse-gesture-actions/releases/latest>

## 方案 A

| 功能 | 触发方式 | 动作 |
|---|---|---|
| 复制 | 右键按住 + 滚轮向上 | 立即发送 `Ctrl+C` |
| 增强粘贴 | 右键按住 + 滚轮向下 | 立即新建文件夹并粘贴剪贴板内容 |
| 侧键截图 | 右键按住 + 已确认保存的侧键 | 调用 `Win+Shift+S` |

每次按住右键最多执行一个动作。未触发动作时，松开右键会回放原生右键单击；已执行动作时不会额外弹出右键菜单。

## 判定规则

- 上滚立即复制，不再等待时间窗口。
- 下滚立即执行增强粘贴。
- 上滚→下滚不再识别为截图；同一次右键保持只执行先发生的动作。
- 右键按住时，已确认保存的 `XButton1` 或 `XButton2` 可立即截图。
- 未按右键时，已启动映射的侧键发送自定义快捷键并替代浏览器原生动作。
- 未启动映射的侧键完整透传给浏览器。
- 普通鼠标左键始终透传。

## 自定义键盘映射键

功能首页的“快捷工具”上方提供两组独立映射。每组均可选择：

- 鼠标侧键：`X1 / 上一页侧键` 或 `X2 / 下一页侧键`。
- 修饰键：`Ctrl`、`Alt`、`Shift`，可任意组合，也可全部不选。
- 主键：`A-Z`。
- 状态：通过该组右侧的“启动/停用”按钮立即切换。

默认配置为：

```text
映射 1：X1 → Ctrl+C（初始关闭）
映射 2：X2 → Ctrl+V（初始关闭）
```

同一侧键最多启动一组映射；若两组选择相同侧键，后启动或后修改的一组生效，另一组自动停用。配置和启用状态会立即保存。

输入优先级固定为：

```text
鼠标按键测试页透传
> 右键保持 + 已确认侧键截图
> 普通侧键键盘映射
> 浏览器原生前进/后退
```

启动任意键盘映射时会自动开启全局监听。手动暂停组合监听后，右键动作和键盘映射都会暂停。

## 增强粘贴

增强粘贴只在以下位置执行：

- 当前激活的 Windows 文件资源管理器窗口。
- Windows 桌面。

程序先发送 `Ctrl+Shift+N` 新建文件夹，等待重命名输入框出现，再发送 `Ctrl+V`。当前前台程序不是资源管理器或桌面时，动作会被拒绝，不会在错误位置创建文件夹。

剪贴板内容须能作为文件夹名称使用，Windows 禁止的文件名字符仍受系统规则限制。

## 鼠标按键测试

在左侧功能栏进入“鼠标按键测试”，可检测以下输入：

| 图示区域 | 检测内容 |
|---|---|
| 左键、右键 | 按下时高亮，抬起时恢复 |
| 中键 | 按下滚轮时高亮，松开时恢复 |
| 滚轮向上、滚轮向下 | 按滚动方向短暂闪烁 |
| `XButton1`、`XButton2` | 检测上一页和下一页侧键 |

测试页会显示最后检测结果，并分别累计七类输入的触发次数。测试期间进入只读模式，所有鼠标消息继续透传给 Windows，不会执行复制、增强粘贴或截图；离开测试页后恢复进入前的组合监听状态。

侧键无反应或截图失败时，可按以下步骤重新确认：

1. 单击“重新确认侧键”。
2. 按下可用的上一页、下一页侧键，图示和计数必须有响应。
3. 单击“保存检测结果”。
4. 返回功能首页，使用“右键按住 + 已确认侧键”调用截图。

可只保存一枚检测正常的侧键，也可保存两枚。保存后立即生效并写入设置文件，无需重启。若按侧键时图示完全没有响应，需要先在鼠标驱动中将侧键恢复为“浏览器上一页/下一页（`XButton1/XButton2`）”，软件无法替代硬件或驱动产生缺失的侧键信号。

## 界面工具

- 左侧功能导航：在功能首页和鼠标按键测试之间切换。
- 鼠标统计器：左键、右键次数、鼠标移动像素距离和各功能成功使用次数。
- 自定义键盘映射：两组 `X1/X2` 到 `Ctrl/Alt/Shift+A-Z` 的独立映射。
- 快捷启动：计算器、系统默认浏览器和 Windows 媒体播放器。
- 显示调节：亮度和对比度分别提供降低、提高按钮。
- 自定义按钮：两个按钮均可右键编辑名称和打开目标。
- 随机鼓励语：启动时随机显示，也可单击“换一句”。
- 统计清零：清除本次运行的统计数据。

内置屏幕亮度优先使用 Windows WMI；外接显示器亮度和对比度使用 DDC/CI。硬件不支持时会显示失败原因。

设置保存在：

```text
%APPDATA%\MouseGestureActions\settings.json
```

V1.0-V1.6 配置可继续读取；旧配置默认启用两枚截图侧键，并生成两组初始关闭的键盘映射。已移除的轨迹和组合窗口字段会被自动忽略。

## 已移除功能

当前版本不再使用轨迹绘制，并已移除：

- 逆时针、顺时针圆圈识别。
- 对勾截图识别。
- 同方向双快划新建目录。
- 删除和回车确认动作。
- 旧版轨迹灵敏度和双划间隔设置。
- 滚轮“上滚→下滚”组合截图。
- `200-300ms` 截图组合窗口及其界面设置。

增强粘贴仍包含“新建文件夹”步骤，但旧版独立新建目录手势已移除。

## 版本说明

- [V1.7 版本说明（仅本地版本）](docs/releases/V1.7.md)
- [V1.6 版本说明](docs/releases/V1.6.md)
- [GitHub Releases](https://github.com/szboboxing/mouse-gesture-actions/releases)

## 版本与发布

- 版本从 `V1.0` 开始按 `Vx.y` 递增。
- 唯一版本来源是 `version.py` 中的 `APP_VERSION`。
- Git 标签、版本文档和 GitHub Release 使用相同版本号。
- 每次构建后，本地 `dist` 只保留版本号最高的一个 EXE。
- 本地使用中文文件名，GitHub Release 使用 `mouse-gesture-actions-Vx.y.exe`。
- Release 同时发布 `SHA256.txt`。

发布新版本：

1. 更新 `version.py`、功能、测试和 `docs/releases/Vx.y.md`。
2. 运行 `.\build.ps1`。
3. 提交代码并推送同名版本标签。
4. GitHub Actions 校验版本、测试、构建并创建 Release。

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
dist\鼠标手势动作小工具_V1.7.exe
```

## 权限与限制

- 普通权限程序不能向管理员权限窗口发送按键，目标程序以管理员身份运行时，本工具也需要相同权限。
- 侧键需要鼠标硬件和驱动向 Windows 上报 `XButton1` 或 `XButton2`。
- 若鼠标驱动把侧键映射成键盘快捷键，需先在驱动中恢复为浏览器前进/后退侧键，再执行重新确认。
- 对比度调节依赖显示器 DDC/CI 支持。

## 开源许可

本项目采用 [MIT License](LICENSE)。
