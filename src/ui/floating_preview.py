"""Linux 浮动预览窗口，使用 PyQt5 在独立线程中运行事件循环。"""

from __future__ import annotations

import subprocess
import threading
import queue
from ..utils.logger import logger
from typing import Optional, Tuple

from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


def _get_active_window_id() -> str:
    """Get the X11 window ID of the currently active window."""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=1
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _restore_focus(window_id: str) -> None:
    """Restore focus to a previously active window."""
    if window_id:
        try:
            subprocess.run(
                ["xdotool", "windowactivate", window_id],
                capture_output=True, timeout=1
            )
        except Exception:
            pass


def _get_active_window_position() -> Tuple[float, float]:
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
        self._queue: queue.Queue = queue.Queue()
        self._prev_window: str = ""
        self._restore_timer: Optional[QTimer] = None
        self._started = threading.Event()
        self._thread = threading.Thread(target=self._run_qt_loop, daemon=True)
        self._thread.start()
        self._started.wait(timeout=5)

    def _run_qt_loop(self) -> None:
        self._app = QApplication.instance()
        if self._app is None:
            self._app = QApplication([])

        self._widget = QWidget()
        self._widget.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus |
            Qt.Tool
        )
        self._widget.setAttribute(Qt.WA_ShowWithoutActivating)
        self._widget.setAttribute(Qt.WA_TranslucentBackground)
        self._widget.setStyleSheet("""
            QWidget {
                background-color: rgba(25, 25, 25, 220);
                border-radius: 10px;
            }
        """)
        self._label = QLabel("", self._widget)
        self._label.setFont(QFont("Noto Sans CJK SC", int(self._font_size)))
        self._label.setStyleSheet("color: white; padding: 8px 12px;")
        self._label.setWordWrap(False)
        self._label.setMaximumWidth(self._max_width)
        layout = QVBoxLayout(self._widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        self._widget.adjustSize()

        # Pre-map the window offscreen so X11 WM registers it before first use.
        # This prevents the window manager from treating the first real show()
        # as a "new window" event that could steal focus.
        self._widget.move(-10000, -10000)
        self._widget.show()
        self._widget.hide()

        timer = QTimer()
        timer.timeout.connect(self._process_pending)
        timer.start(50)
        self._started.set()
        logger.info(f"[FloatingPreview] Qt event loop started in thread={threading.current_thread().name}")
        self._app.exec_()

    def _process_pending(self) -> None:
        while True:
            try:
                action, text = self._queue.get_nowait()
            except queue.Empty:
                return
            logger.info(f"[FloatingPreview] Processing: action={action}, text={text}")
            if action == "show":
                self._prev_window = _get_active_window_id()
                # Cancel any pending restore timer from previous show
                if self._restore_timer is not None:
                    self._restore_timer.stop()
                    self._restore_timer = None
                if self._label:
                    self._label.setText(text or "正在聆听...")
                x, y = _get_active_window_position()
                if self._widget:
                    self._widget.move(int(x), int(y) + 30)
                    self._widget.adjustSize()
                    self._widget.show()
                    self._widget.raise_()
                    # Re-assert non-activating attribute after raise
                    self._widget.setAttribute(Qt.WA_ShowWithoutActivating)
                    # Three-stage focus restore to handle async WM behavior
                    if self._prev_window:
                        wid = self._prev_window
                        QTimer.singleShot(30, lambda w=wid: _restore_focus(w))
                        QTimer.singleShot(100, lambda w=wid: _restore_focus(w))
                        self._restore_timer = QTimer()
                        self._restore_timer.setSingleShot(True)
                        self._restore_timer.timeout.connect(lambda w=wid: _restore_focus(w))
                        self._restore_timer.start(300)
                    logger.info(f"[FloatingPreview] Widget shown at ({x}, {y + 30})")
            elif action == "hide":
                if self._widget:
                    self._widget.hide()
                # Restore focus to the previously active window
                if self._prev_window:
                    _restore_focus(self._prev_window)
                    self._prev_window = ""
                # Cancel any pending restore timer
                if self._restore_timer is not None:
                    self._restore_timer.stop()
                    self._restore_timer = None
                logger.info("[FloatingPreview] Widget hidden, focus restored")
            elif action == "update_text":
                if self._label and text is not None:
                    display = text
                    if len(text) > 100:
                        display = "..." + text[-97:]
                    self._label.setText(display if display else "正在聆听...")
                if self._widget and self._widget.isVisible():
                    self._widget.adjustSize()
                logger.info(f"[FloatingPreview] Text updated to '{text}', widget visible={self._widget.isVisible() if self._widget else False}")

    def show(self) -> None:
        logger.info(f"[FloatingPreview] show() called from thread={threading.current_thread().name}")
        self._queue.put(("show", "正在聆听..."))

    def hide(self) -> None:
        self._queue.put(("hide", None))

    def update_text(self, text: str) -> None:
        logger.info(f"[FloatingPreview] update_text('{text}') called")
        self._queue.put(("update_text", text))
