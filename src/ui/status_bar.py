"""Linux 状态栏控制器，使用终端输出显示 Whisper-Input 的运行状态。"""

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
    """Linux 状态栏控制器，使用终端打印状态信息。"""

    def __init__(self) -> None:
        self._current_state: InputState = InputState.IDLE
        self._queue_length: int = 0

    def start(self) -> None:
        """启动状态栏（Linux 上为空操作，由键盘监听器保持进程运行）。"""
        print("[StatusBar] 状态栏已启动 (Linux 模式 - 终端输出)")
        print("[StatusBar] 按 Ctrl+F 开始/结束语音输入 (豆包流式)")
        print("[StatusBar] 按 Ctrl+I 开始/结束语音输入 (本地 Whisper)")
        print("[StatusBar] 按 Ctrl+C 退出程序")
        # 阻塞主线程，等待键盘监听器工作
        try:
            import signal
            signal.pause()
        except (KeyboardInterrupt, SystemExit):
            print("\n[StatusBar] 正在退出...")

    def update_state(
        self,
        state: InputState,
        *,
        queue_length: int = 0,
    ) -> None:
        """更新状态显示，输出到终端。"""
        self._current_state = state
        self._queue_length = queue_length
        visual = _STATE_VISUALS.get(state, _STATE_VISUALS[InputState.IDLE])
        queue_info = f" | 待处理: {queue_length}" if queue_length else ""
        print(f"\r[状态] {visual.fallback_text} {visual.description}{queue_info}", end="", flush=True)

    def show_error(self, message: str) -> None:
        """显示错误信息。"""
        print(f"\n[错误] {message}")
