from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from gui import APP_NAME, MainWindow


def test_main_window_can_be_created() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert APP_NAME in window.windowTitle()
    assert window.parse_button.text() == "解析视频"
    assert window.download_button.isEnabled() is False

    window.close()
    app.processEvents()
