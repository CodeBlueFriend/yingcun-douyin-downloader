from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import QObject, QSize, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from downloader.download import DouyinDownloader, DownloadError, DownloadResult, VideoInfo
from downloader.parser import LinkParseError, extract_share_url, resolve_share_url
from downloader.quality import Quality
from downloader.utils import configure_logging, format_duration

APP_NAME = "映存"
QUALITY_LABELS = {
    "原画 / 最高可用": Quality.BEST,
    "1080p": Quality.P1080,
    "720p": Quality.P720,
    "540p": Quality.P540,
    "最低清晰度": Quality.WORST,
}

STYLE = """
QMainWindow, QWidget#root {
    background: #0b1020;
    color: #e8ecf8;
}
QLabel#brand { color: #8ea7ff; font-size: 13px; font-weight: 700; letter-spacing: 2px; }
QLabel#title { color: #f8f9ff; font-size: 30px; font-weight: 750; }
QLabel#subtitle { color: #8f99b2; font-size: 13px; }
QLabel#section { color: #f2f4ff; font-size: 15px; font-weight: 700; }
QLabel#muted { color: #8993ac; font-size: 12px; }
QLabel#videoTitle { color: #f5f6ff; font-size: 17px; font-weight: 700; }
QLabel#status { color: #aeb7cd; font-size: 12px; }
QFrame#card {
    background: #131a2f;
    border: 1px solid #242d49;
    border-radius: 16px;
}
QTextEdit, QLineEdit, QComboBox {
    background: #0e1528;
    color: #eef1fb;
    border: 1px solid #2b3657;
    border-radius: 10px;
    padding: 9px 11px;
    selection-background-color: #657cff;
}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus { border: 1px solid #7186ff; }
QComboBox::drop-down { border: 0; width: 28px; }
QPushButton {
    background: #202a47;
    color: #e9edff;
    border: 1px solid #334066;
    border-radius: 10px;
    padding: 9px 16px;
    font-weight: 650;
}
QPushButton:hover { background: #293658; border-color: #52628d; }
QPushButton:pressed { background: #18213a; }
QPushButton:disabled { color: #65708b; background: #171e33; border-color: #252d47; }
QPushButton#primary {
    background: #667cff;
    color: white;
    border: 0;
    padding: 10px 22px;
}
QPushButton#primary:hover { background: #778bff; }
QPushButton#primary:pressed { background: #576de9; }
QProgressBar {
    background: #0d1427;
    border: 0;
    border-radius: 6px;
    height: 11px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk { background: #6c83ff; border-radius: 6px; }
QToolTip { background: #171f36; color: white; border: 1px solid #394669; }
"""


class InfoWorker(QObject):
    succeeded = Signal(object, object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, share_text: str, output: Path, cookies: Path | None) -> None:
        super().__init__()
        self.share_text = share_text
        self.output = output
        self.cookies = cookies

    @Slot()
    def run(self) -> None:
        try:
            share_url = extract_share_url(self.share_text)
            resolved_url = resolve_share_url(share_url)
            client = DouyinDownloader(self.output, self.cookies)
            self.succeeded.emit(client.fetch_info(resolved_url), client)
        except (LinkParseError, DownloadError) as exc:
            self.failed.emit(str(exc))
        except Exception:
            logging.getLogger(__name__).exception("GUI metadata worker failed")
            self.failed.emit("解析时发生未知错误，请查看日志")
        finally:
            self.finished.emit()


class DownloadWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str, str)
    finished = Signal()

    def __init__(
        self, client: DouyinDownloader, info: VideoInfo, quality: Quality
    ) -> None:
        super().__init__()
        self.client = client
        self.info = info
        self.quality = quality

    def _progress_hook(self, status: Mapping[str, Any]) -> None:
        if status.get("status") != "downloading":
            return
        downloaded = int(status.get("downloaded_bytes") or 0)
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        percent = int(downloaded * 100 / total) if total else 0
        speed = status.get("speed")
        eta = status.get("eta")
        speed_text = f"{speed / 1024 / 1024:.2f} MiB/s" if speed else "计算中"
        eta_text = f"约 {int(eta)} 秒" if eta is not None else "计算中"
        self.progress.emit(max(0, min(percent, 100)), speed_text, eta_text)

    @Slot()
    def run(self) -> None:
        try:
            result = self.client.download(
                self.info, self.quality, progress_hook=self._progress_hook
            )
            self.succeeded.emit(result)
        except DownloadError as exc:
            self.failed.emit(str(exc))
        except Exception:
            logging.getLogger(__name__).exception("GUI download worker failed")
            self.failed.emit("下载时发生未知错误，请查看日志")
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.output_dir = (Path.cwd() / "downloads").resolve()
        self.cookies_file: Path | None = None
        self.video_info: VideoInfo | None = None
        self.client: DouyinDownloader | None = None
        self.last_result: DownloadResult | None = None
        self._threads: set[QThread] = set()
        self.network = QNetworkAccessManager(self)

        self.setWindowTitle(f"{APP_NAME} · 抖音公开视频下载")
        self.setMinimumSize(QSize(920, 680))
        self.resize(1060, 760)
        self._build_ui()
        self._set_ready(False)

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        return card, layout

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(42, 30, 42, 30)
        page.setSpacing(18)

        brand = QLabel("YINGCUN  /  PUBLIC MEDIA")
        brand.setObjectName("brand")
        title = QLabel("保存你有权拥有的公开影像")
        title.setObjectName("title")
        subtitle = QLabel("粘贴抖音分享文本，解析信息并选择合适清晰度。仅支持正常公开访问。")
        subtitle.setObjectName("subtitle")
        page.addWidget(brand)
        page.addWidget(title)
        page.addWidget(subtitle)

        input_card, input_layout = self._card()
        input_header = QHBoxLayout()
        section = QLabel("分享内容")
        section.setObjectName("section")
        hint = QLabel("支持短链或包含中文文案的完整分享文本")
        hint.setObjectName("muted")
        input_header.addWidget(section)
        input_header.addStretch()
        input_header.addWidget(hint)
        input_layout.addLayout(input_header)
        self.share_input = QTextEdit()
        self.share_input.setPlaceholderText("在此粘贴 https://v.douyin.com/... 或完整分享文本")
        self.share_input.setFixedHeight(82)
        input_layout.addWidget(self.share_input)

        action_row = QHBoxLayout()
        self.output_edit = QLineEdit(str(self.output_dir))
        self.output_edit.setReadOnly(True)
        self.output_edit.setToolTip("视频和日志的保存目录")
        browse_button = QPushButton("选择目录")
        browse_button.clicked.connect(self._choose_output)
        self.cookie_button = QPushButton("授权 Cookies（可选）")
        self.cookie_button.clicked.connect(self._choose_cookies)
        self.parse_button = QPushButton("解析视频")
        self.parse_button.setObjectName("primary")
        self.parse_button.clicked.connect(self._parse)
        action_row.addWidget(self.output_edit, 1)
        action_row.addWidget(browse_button)
        action_row.addWidget(self.cookie_button)
        action_row.addWidget(self.parse_button)
        input_layout.addLayout(action_row)
        page.addWidget(input_card)

        content_row = QHBoxLayout()
        content_row.setSpacing(18)
        info_card, info_layout = self._card()
        info_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        info_title = QLabel("视频信息")
        info_title.setObjectName("section")
        info_layout.addWidget(info_title)
        info_body = QHBoxLayout()
        info_body.setSpacing(18)
        self.cover = QLabel("封面预览")
        self.cover.setObjectName("muted")
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setFixedSize(180, 230)
        self.cover.setStyleSheet("background:#0d1427;border-radius:12px;")
        info_body.addWidget(self.cover)
        metadata = QVBoxLayout()
        self.video_title = QLabel("等待解析")
        self.video_title.setObjectName("videoTitle")
        self.video_title.setWordWrap(True)
        self.author_label = QLabel("作者  —")
        self.duration_label = QLabel("时长  —")
        self.formats_label = QLabel("清晰度  —")
        for label in (self.author_label, self.duration_label, self.formats_label):
            label.setObjectName("muted")
        metadata.addWidget(self.video_title)
        metadata.addSpacing(6)
        metadata.addWidget(self.author_label)
        metadata.addWidget(self.duration_label)
        metadata.addWidget(self.formats_label)
        metadata.addStretch()
        info_body.addLayout(metadata, 1)
        info_layout.addLayout(info_body)
        content_row.addWidget(info_card, 3)

        download_card, download_layout = self._card()
        download_card.setMinimumWidth(310)
        download_title = QLabel("下载设置")
        download_title.setObjectName("section")
        download_layout.addWidget(download_title)
        quality_hint = QLabel("目标清晰度")
        quality_hint.setObjectName("muted")
        download_layout.addWidget(quality_hint)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_LABELS.keys())
        download_layout.addWidget(self.quality_combo)
        download_layout.addSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        download_layout.addWidget(self.progress_bar)
        metrics = QHBoxLayout()
        self.speed_label = QLabel("速度  —")
        self.eta_label = QLabel("剩余  —")
        self.speed_label.setObjectName("muted")
        self.eta_label.setObjectName("muted")
        metrics.addWidget(self.speed_label)
        metrics.addStretch()
        metrics.addWidget(self.eta_label)
        download_layout.addLayout(metrics)
        self.download_button = QPushButton("开始下载")
        self.download_button.setObjectName("primary")
        self.download_button.clicked.connect(self._download)
        self.open_button = QPushButton("打开保存目录")
        self.open_button.clicked.connect(self._open_output)
        download_layout.addStretch()
        download_layout.addWidget(self.download_button)
        download_layout.addWidget(self.open_button)
        content_row.addWidget(download_card, 2)
        page.addLayout(content_row, 1)

        footer = QHBoxLayout()
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("status")
        compliance = QLabel("仅下载你有权保存的公开视频 · 不绕过平台限制")
        compliance.setObjectName("muted")
        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(compliance)
        page.addLayout(footer)

    def _set_busy(self, busy: bool, status: str) -> None:
        self.parse_button.setDisabled(busy)
        self.download_button.setDisabled(busy or self.video_info is None)
        self.status_label.setText(status)

    def _set_ready(self, ready: bool) -> None:
        self.download_button.setEnabled(ready)

    def _start_worker(self, worker: QObject, run_slot: Any) -> None:
        thread = QThread(self)
        self._threads.add(thread)
        worker.moveToThread(thread)
        thread.started.connect(run_slot)
        worker.destroyed.connect(lambda: None)
        thread.finished.connect(lambda: self._threads.discard(thread))
        thread.finished.connect(thread.deleteLater)
        setattr(thread, "worker", worker)
        thread.start()

    @Slot()
    def _choose_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "选择保存目录", str(self.output_dir)
        )
        if selected:
            self.output_dir = Path(selected).resolve()
            self.output_edit.setText(str(self.output_dir))
            configure_logging(self.output_dir / "douyin_downloader.log")

    @Slot()
    def _choose_cookies(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "选择 Netscape Cookies 文件", "", "Text files (*.txt);;All files (*)"
        )
        if selected:
            self.cookies_file = Path(selected).resolve()
            self.cookie_button.setText("Cookies 已授权")
            self.cookie_button.setToolTip(str(self.cookies_file))

    @Slot()
    def _parse(self) -> None:
        text = self.share_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "需要分享链接", "请先粘贴抖音分享链接或分享文本。")
            return
        self.video_info = None
        self.client = None
        self._set_busy(True, "正在解析公开页面，请稍候…")
        worker = InfoWorker(text, self.output_dir, self.cookies_file)
        thread_finished = worker.finished
        worker.succeeded.connect(self._info_ready)
        worker.failed.connect(self._operation_failed)
        thread_finished.connect(worker.deleteLater)
        self._start_worker(worker, worker.run)
        thread_finished.connect(worker.thread().quit)

    @Slot(object, object)
    def _info_ready(self, info: VideoInfo, client: DouyinDownloader) -> None:
        self.video_info = info
        self.client = client
        self.video_title.setText(info.title)
        self.author_label.setText(f"作者  {info.author}")
        self.duration_label.setText(f"时长  {format_duration(info.duration)}")
        formats = " / ".join(f"{item.height}p" for item in info.formats)
        self.formats_label.setText(f"清晰度  {formats}")
        self._set_busy(False, "解析完成，可以选择清晰度下载")
        if info.thumbnail:
            reply = self.network.get(QNetworkRequest(QUrl(info.thumbnail)))
            reply.finished.connect(lambda: self._cover_ready(reply))

    @Slot()
    def _download(self) -> None:
        if self.video_info is None or self.client is None:
            return
        quality = QUALITY_LABELS[self.quality_combo.currentText()]
        self.progress_bar.setValue(0)
        self.speed_label.setText("速度  计算中")
        self.eta_label.setText("剩余  计算中")
        self._set_busy(True, "正在下载媒体文件…")
        worker = DownloadWorker(self.client, self.video_info, quality)
        thread_finished = worker.finished
        worker.progress.connect(self._update_progress)
        worker.succeeded.connect(self._download_ready)
        worker.failed.connect(self._operation_failed)
        thread_finished.connect(worker.deleteLater)
        self._start_worker(worker, worker.run)
        thread_finished.connect(worker.thread().quit)

    @Slot(int, str, str)
    def _update_progress(self, percent: int, speed: str, eta: str) -> None:
        self.progress_bar.setValue(percent)
        self.speed_label.setText(f"速度  {speed}")
        self.eta_label.setText(f"剩余  {eta}")

    @Slot(object)
    def _download_ready(self, result: DownloadResult) -> None:
        self.last_result = result
        self.progress_bar.setValue(100)
        self._set_busy(False, result.notice or f"下载完成：{result.path.name}")
        QMessageBox.information(self, "下载完成", f"视频已保存到：\n{result.path}")

    @Slot(str)
    def _operation_failed(self, message: str) -> None:
        self._set_busy(False, "操作失败，请检查提示")
        QMessageBox.warning(self, "操作未完成", message)

    @Slot()
    def _open_output(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    def _cover_ready(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                pixmap = QPixmap()
                if pixmap.loadFromData(reply.readAll()):
                    scaled = pixmap.scaled(
                        self.cover.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.cover.setPixmap(scaled)
        finally:
            reply.deleteLater()

    def closeEvent(self, event: Any) -> None:
        if any(thread.isRunning() for thread in self._threads):
            QMessageBox.information(self, "任务进行中", "请等待当前解析或下载任务完成。")
            event.ignore()
            return
        event.accept()


def main() -> int:
    configure_logging((Path.cwd() / "downloads" / "douyin_downloader.log").resolve())
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Arial", 10))
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
