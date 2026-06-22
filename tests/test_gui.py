from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    pytest.skip(f"Qt system libraries are unavailable: {exc}", allow_module_level=True)

from gui import APP_NAME, MainWindow


def test_main_window_can_be_created() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert APP_NAME in window.windowTitle()
    assert window.parse_button.text() == "解析视频"
    assert window.download_button.isEnabled() is False

    window.close()
    app.processEvents()
