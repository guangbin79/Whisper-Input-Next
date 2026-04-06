# Ubuntu 22.04 中文实时语音输入法安装指南

> Whisper-Input-Next — 基于豆包流式 ASR 的开源语音输入工具，按下快捷键说话，文字自动输入到光标处。

## 前置条件

- Ubuntu 22.04 LTS (Jammy)
- sudo 权限
- 麦克风设备
- 网络连接（安装依赖 + 豆包 ASR 云端调用）

## 1. 安装 Python 3.12

Ubuntu 22.04 默认 Python 3.10，项目要求 3.12+。通过 deadsnakes PPA 安装：

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

## 2. 安装系统依赖

```bash
sudo apt install -y \
  git xdotool xclip pulseaudio-utils \
  libportaudio2 libportaudiocpp0 portaudio19-dev \
  python3-xlib libx11-dev libxtst-dev
```

| 包名 | 用途 |
|------|------|
| xdotool | 模拟键盘输入，将识别文字输入到光标处 |
| xclip | 剪贴板操作 |
| pulseaudio-utils | 音频设备管理 |
| libportaudio2 / portaudio19-dev | sounddevice 的底层音频库 |
| python3-xlib, libx11-dev, libxtst-dev | pynput 全局热键监听在 Linux 上的依赖 |

## 3. 克隆仓库

```bash
git clone https://github.com/Mor-Li/Whisper-Input-Next.git ~/Whisper-Input-Next
cd ~/Whisper-Input-Next
```

## 4. 创建虚拟环境并安装 Python 依赖

```bash
python3.12 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements-linux.txt
```

> `requirements-linux.txt` 已排除 macOS 专用的 `pyobjc-*`，包含 Linux 所需的全部依赖。

## 5. 配置环境变量

```bash
cp env.example .env
```

编辑 `.env`，关键配置：

```bash
# 豆包流式 ASR（默认转录服务）
DOUBAO_APP_KEY=你的APP_ID
DOUBAO_ACCESS_KEY=你的Access_Token
TRANSCRIPTION_SERVICE=doubao

# 平台设为 linux
SYSTEM_PLATFORM=linux

# 快捷键
TRANSCRIPTIONS_BUTTON=f
TRANSLATIONS_BUTTON=ctrl

# 功能开关
CONVERT_TO_SIMPLIFIED=false
ADD_SYMBOL=false
OPTIMIZE_RESULT=false
ENABLE_KIMI_POLISH=false
AUTO_RETRY_LIMIT=5
```

### 获取豆包 API Key

1. 访问 [火山引擎控制台 - 语音识别](https://console.volcengine.com/ark/region:ark+cn-beijing/tts/speechRecognition)
2. 登录/注册火山引擎账号
3. 在「服务接口认证信息」中获取 **APP ID** 和 **Access Token**
4. 分别填入 `DOUBAO_APP_KEY` 和 `DOUBAO_ACCESS_KEY`

## 6. Linux 兼容性修复

项目原生仅支持 macOS，以下三处需要修改以适配 Linux。

### 6.1 键盘修饰键映射

文件：`src/keyboard/listener.py`

原始代码非 Windows 平台默认用 `Key.cmd`（macOS Command 键），Linux 上需改为 `Key.ctrl`：

```python
# 修改前
sysetem_platform = os.getenv("SYSTEM_PLATFORM")
if sysetem_platform == "win" :
    self.sysetem_platform = Key.ctrl
    logger.info("配置到Windows平台")
else:
    self.sysetem_platform = Key.cmd
    logger.info("配置到Mac平台")

# 修改后
sysetem_platform = os.getenv("SYSTEM_PLATFORM", "mac")
if sysetem_platform == "win":
    self.sysetem_platform = Key.ctrl
    logger.info("配置到Windows平台")
elif sysetem_platform == "linux":
    self.sysetem_platform = Key.ctrl
    logger.info("配置到Linux平台")
else:
    self.sysetem_platform = Key.cmd
    logger.info("配置到Mac平台")
```

### 6.2 状态栏 — 替换 macOS AppKit 为终端输出

文件：`src/ui/status_bar.py`

原文件依赖 `AppKit`、`Cocoa`、`PyObjCTools`（macOS 专用）。备份原文件后，用终端输出替代：

```bash
cp src/ui/status_bar.py src/ui/status_bar_mac.py
```

替换为以下内容（保持 `StatusBarController` 接口不变）：

```python
"""Linux 状态栏控制器，使用终端输出。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Optional

from src.keyboard.inputState import InputState


@dataclass(frozen=True)
class _StateVisual:
    fallback_text: str
    description: str
    env_key: str


_STATE_VISUALS = {
    InputState.IDLE: _StateVisual("🎙️", "空闲", "IDLE"),
    InputState.RECORDING: _StateVisual("🔴", "录音中 (OpenAI)", "RECORDING"),
    InputState.RECORDING_TRANSLATE: _StateVisual("🔴", "录音中 (翻译)", "RECORDING"),
    InputState.RECORDING_KIMI: _StateVisual("🟠", "录音中 (本地 Whisper)", "RECORDING"),
    InputState.DOUBAO_STREAMING: _StateVisual("🟢", "流式识别中 (豆包)", "RECORDING"),
    InputState.PROCESSING: _StateVisual("🔵", "转录处理中", "PROCESSING"),
    InputState.PROCESSING_KIMI: _StateVisual("🔵", "转录处理中", "PROCESSING"),
    InputState.TRANSLATING: _StateVisual("🟡", "翻译中", "PROCESSING"),
    InputState.WARNING: _StateVisual("⚠️", "警告", "PROCESSING"),
    InputState.ERROR: _StateVisual("❗️", "错误", "PROCESSING"),
}


class StatusBarController:

    def __init__(self) -> None:
        self._current_state: InputState = InputState.IDLE
        self._queue_length: int = 0

    def start(self) -> None:
        print("[StatusBar] 按 Ctrl+F 开始/结束语音输入 (豆包流式)")
        print("[StatusBar] 按 Ctrl+I 开始/结束语音输入 (本地 Whisper)")
        print("[StatusBar] 按 Ctrl+C 退出程序")
        try:
            import signal
            signal.pause()
        except (KeyboardInterrupt, SystemExit):
            print("\n[StatusBar] 正在退出...")

    def update_state(self, state: InputState, *, queue_length: int = 0) -> None:
        self._current_state = state
        self._queue_length = queue_length
        visual = _STATE_VISUALS.get(state, _STATE_VISUALS[InputState.IDLE])
        queue_info = f" | 待处理: {queue_length}" if queue_length else ""
        print(f"\r[状态] {visual.fallback_text} {visual.description}{queue_info}", end="", flush=True)

    def show_error(self, message: str) -> None:
        print(f"\n[错误] {message}")
```

### 6.3 浮动预览窗口 — 替换 macOS AppKit 为 PyQt5

文件：`src/ui/floating_preview.py`

原文件依赖 `AppKit`、`ApplicationServices`、`Cocoa`（macOS 专用）。备份原文件后，用 PyQt5 替代：

```bash
cp src/ui/floating_preview.py src/ui/floating_preview_mac.py
```

替换为以下内容（保持 `FloatingPreviewWindow` 接口不变）：

```python
"""Linux 浮动预览窗口，使用 PyQt5。"""

from __future__ import annotations

import subprocess
from typing import Optional, Tuple

from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt


def _get_active_window_cursor_pos() -> Tuple[float, float]:
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowgeometry"],
            capture_output=True, text=True, timeout=2
        )
        for line in result.stdout.splitlines():
            if "Position:" in line:
                parts = line.strip().split()
                x, y = int(parts[1].rstrip(",")), int(parts[2])
                return (float(x), float(y))
    except Exception:
        pass
    return (100.0, 100.0)


class FloatingPreviewWindow:

    def __init__(self, max_width: int = 600, font_size: float = 16.0) -> None:
        self._max_width = max_width
        self._font_size = font_size
        self._widget: Optional[QWidget] = None
        self._label: Optional[QLabel] = None
        self._app: Optional[QApplication] = None

    def _ensure_app(self) -> None:
        if self._app is None:
            self._app = QApplication.instance()
            if self._app is None:
                self._app = QApplication([])

    def _ensure_widget(self) -> None:
        if self._widget is not None:
            return
        self._ensure_app()
        self._widget = QWidget()
        self._widget.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self._widget.setAttribute(Qt.WA_TranslucentBackground)
        self._widget.setStyleSheet(
            "QWidget { background-color: rgba(25,25,25,220); border-radius: 10px; }"
        )
        from PyQt5.QtGui import QFont
        self._label = QLabel("正在聆听...", self._widget)
        self._label.setFont(QFont("Noto Sans CJK SC", self._font_size))
        self._label.setStyleSheet("color: white; padding: 8px 12px;")
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(self._max_width)
        self._widget.adjustSize()
        self._widget.hide()

    def show(self) -> None:
        self._ensure_widget()
        if self._label:
            self._label.setText("正在聆听...")
        x, y = _get_active_window_cursor_pos()
        if self._widget:
            self._widget.move(int(x), int(y) + 30)
            self._widget.adjustSize()
            self._widget.show()

    def hide(self) -> None:
        if self._widget:
            self._widget.hide()

    def update_text(self, text: str) -> None:
        if self._label is None:
            return
        display_text = text if len(text) <= 100 else "..." + text[-97:]
        self._label.setText(display_text if display_text else "正在聆听...")
        if self._widget and self._widget.isVisible():
            self._widget.adjustSize()
```

### 6.4 OpenAI 处理器可选化

文件：`main.py`

原始代码 OpenAI 处理器初始化失败会直接崩溃。改为可选：

```python
# 修改前
os.environ["SERVICE_PLATFORM"] = "openai"
openai_processor = WhisperProcessor()

# 修改后
os.environ["SERVICE_PLATFORM"] = "openai"
try:
    openai_processor = WhisperProcessor()
except Exception as e:
    logger.warning(f"OpenAI 处理器不可用: {e}")
    openai_processor = None
```

## 7. 权限配置

pynput 全局热键监听在 Linux 上需要权限：

```bash
sudo usermod -aG input $USER
```

**重新登录后生效。**

## 8. 启动

### 前台运行

```bash
cd ~/Whisper-Input-Next
source .venv/bin/activate
python main.py
```

### tmux 后台运行

```bash
cd ~/Whisper-Input-Next
./start.sh
```

### shell alias（推荐）

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
alias whisper='cd ~/Whisper-Input-Next && source .venv/bin/activate && python main.py'
alias whisper_off='tmux kill-session -t Whisper-Input-Next 2>/dev/null'
```

## 9. 使用方式

| 快捷键 | 功能 | 引擎 |
|--------|------|------|
| `Ctrl+F` | 按一下开始录音，再按一下结束 | 豆包流式 ASR（低延迟，实时显示） |
| `Ctrl+I` | 按一下开始录音，再按一下结束 | 本地 whisper.cpp（需额外安装） |

识别完成后，文字自动通过 xdotool 输入到当前光标位置。

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| `PortAudio library not found` | `sudo apt install libportaudio2 portaudio19-dev` |
| `No module named 'AppKit'` | status_bar.py / floating_preview.py 未替换为 Linux 版本 |
| Ctrl+F 无响应 | `sudo usermod -aG input $USER` 然后重新登录 |
| 豆包 ASR 连接失败 | 检查网络，确认 `DOUBAO_APP_KEY` 和 `DOUBAO_ACCESS_KEY` 正确 |
| 音频设备未检测到 | 检查 `pulseaudio` 是否运行：`pulseaudio --check && echo OK` |
| PyQt5 浮动窗口不显示 | 确认 DISPLAY 环境变量：`echo $DISPLAY` |

## 文件结构

```
~/Whisper-Input-Next/
├── .env                          # 环境变量配置（API Key 等）
├── .venv/                        # Python 3.12 虚拟环境
├── main.py                       # 入口（已修改：OpenAI 可选化）
├── start.sh                      # tmux 启动脚本
├── src/
│   ├── keyboard/
│   │   └── listener.py           # 热键监听（已修改：Linux 平台支持）
│   ├── transcription/
│   │   └── doubao_streaming.py   # 豆包流式 ASR 处理器
│   └── ui/
│       ├── status_bar.py         # Linux 状态栏（终端输出版）
│       ├── status_bar_mac.py     # macOS 原版备份
│       ├── floating_preview.py   # Linux 浮动预览（PyQt5 版）
│       └── floating_preview_mac.py  # macOS 原版备份
└── requirements-linux.txt        # Linux 依赖列表（无 pyobjc-*）
└── requirements.txt              # macOS 依赖列表
```
