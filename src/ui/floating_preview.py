"""Linux 浮动预览窗口，使用 PyQt5 显示流式识别中的 pending 文字。"""

from __future__ import annotations

import subprocess
from typing import Optional, Tuple

from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor


def _get_active_window_cursor_pos() -> Tuple[float, float]:
    """通过 xdotool 获取当前光标位置作为浮动窗口定位参考。"""
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
    """Linux 浮动预览窗口，使用 PyQt5 QWidget。"""

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
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self._widget.setAttribute(Qt.WA_TranslucentBackground)
        self._widget.setStyleSheet("""
            QWidget {
                background-color: rgba(25, 25, 25, 220);
                border-radius: 10px;
            }
        """)

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
        display_text = text
        if len(text) > 100:
            display_text = "..." + text[-97:]
        self._label.setText(display_text if display_text else "正在聆听...")
        if self._widget and self._widget.isVisible():
            self._widget.adjustSize()
