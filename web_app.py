from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import uuid
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from downloader.download import DouyinDownloader, DownloadError, VideoInfo
from downloader.parser import LinkParseError, extract_share_url, resolve_share_url
from downloader.quality import Quality
from downloader.utils import configure_logging, format_duration

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
OUTPUT_DIR = ROOT / "downloads"
LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DownloadJob:
    status: str = "queued"
    progress: int = 0
    speed: str = "计算中"
    eta: str = "计算中"
    message: str = "等待下载"
    filename: str | None = None
    saved_path: str | None = None


@dataclass(slots=True)
class AppState:
    sessions: dict[str, VideoInfo] = field(default_factory=dict)
    jobs: dict[str, DownloadJob] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


STATE = AppState()


def _video_payload(session_id: str, info: VideoInfo) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "title": info.title,
        "author": info.author,
        "thumbnail": info.thumbnail,
        "duration": format_duration(info.duration),
        "formats": [f"{item.height}p" for item in info.formats],
    }


def parse_video(share_text: str) -> dict[str, Any]:
    share_url = extract_share_url(share_text)
    resolved_url = resolve_share_url(share_url)
    client = DouyinDownloader(OUTPUT_DIR)
    info = client.fetch_info(resolved_url)
    session_id = uuid.uuid4().hex
    with STATE.lock:
        STATE.sessions[session_id] = info
    return _video_payload(session_id, info)


def resolve_output_dir(value: str) -> Path:
    raw = value.strip() or "./downloads"
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    resolved = candidate.resolve()
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("保存路径指向了文件，请选择文件夹")
    try:
        resolved.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError("无法创建保存目录，请检查路径和写入权限") from exc
    return resolved


def _launch_directory(path: Path) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(
                ["open", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        elif sys.platform == "win32":
            startfile = getattr(os, "startfile")
            startfile(str(path))
        else:
            subprocess.Popen(
                ["xdg-open", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except (AttributeError, OSError) as exc:
        raise ValueError("无法打开文件管理器，请手动打开该保存目录") from exc


def open_output_dir(value: str) -> Path:
    output_dir = resolve_output_dir(value)
    _launch_directory(output_dir)
    return output_dir


def _run_download(
    job_id: str, session_id: str, quality: Quality, output_dir: Path
) -> None:
    with STATE.lock:
        session = STATE.sessions.get(session_id)
        job = STATE.jobs[job_id]
        job.status = "downloading"
        job.message = "正在下载媒体文件"
    if session is None:
        with STATE.lock:
            job.status = "failed"
            job.message = "解析信息已失效，请重新解析视频"
        return

    info = session
    client = DouyinDownloader(output_dir)

    def progress_hook(status: Mapping[str, Any]) -> None:
        if status.get("status") != "downloading":
            return
        downloaded = int(status.get("downloaded_bytes") or 0)
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        progress = int(downloaded * 100 / total) if total else 0
        speed = status.get("speed")
        eta = status.get("eta")
        with STATE.lock:
            job.progress = max(0, min(progress, 100))
            job.speed = f"{speed / 1024 / 1024:.2f} MiB/s" if speed else "计算中"
            job.eta = f"约 {int(eta)} 秒" if eta is not None else "计算中"

    try:
        result = client.download(info, quality, progress_hook=progress_hook)
        with STATE.lock:
            job.status = "complete"
            job.progress = 100
            job.message = result.notice or "下载完成"
            job.filename = result.path.name
            job.saved_path = str(result.path)
    except DownloadError as exc:
        with STATE.lock:
            job.status = "failed"
            job.message = str(exc)
    except Exception:
        LOGGER.exception("web download job failed")
        with STATE.lock:
            job.status = "failed"
            job.message = "下载时发生未知错误，请查看日志"


def start_download(session_id: str, quality_value: str, output_value: str) -> str:
    try:
        quality = Quality(quality_value)
    except ValueError as exc:
        raise ValueError("不支持的清晰度选项") from exc
    output_dir = resolve_output_dir(output_value)
    with STATE.lock:
        if session_id not in STATE.sessions:
            raise ValueError("解析信息已失效，请重新解析视频")
        job_id = uuid.uuid4().hex
        STATE.jobs[job_id] = DownloadJob()
    thread = threading.Thread(
        target=_run_download,
        args=(job_id, session_id, quality, output_dir),
        daemon=True,
        name=f"download-{job_id[:8]}",
    )
    thread.start()
    return job_id


class WebHandler(SimpleHTTPRequestHandler):
    server_version = "YingcunLocal/1.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("web: " + format, *args)

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 64_000:
            raise ValueError("请求内容为空或过大")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求格式无效") from exc
        if not isinstance(value, dict):
            raise ValueError("请求格式无效")
        return value

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.removeprefix("/api/jobs/")
            with STATE.lock:
                job = STATE.jobs.get(job_id)
                payload = (
                    {
                        "status": job.status,
                        "progress": job.progress,
                        "speed": job.speed,
                        "eta": job.eta,
                        "message": job.message,
                        "filename": job.filename,
                        "saved_path": job.saved_path,
                    }
                    if job
                    else None
                )
            if payload is None:
                self._send_json({"error": "下载任务不存在"}, HTTPStatus.NOT_FOUND)
            else:
                self._send_json(payload)
            return
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self._json_body()
            if parsed.path == "/api/parse":
                share_text = str(body.get("share_text") or "").strip()
                if not share_text:
                    raise ValueError("请粘贴抖音分享链接或分享文本")
                self._send_json(parse_video(share_text))
                return
            if parsed.path == "/api/download":
                job_id = start_download(
                    str(body.get("session_id") or ""),
                    str(body.get("quality") or "best"),
                    str(body.get("output_dir") or "./downloads"),
                )
                self._send_json({"job_id": job_id}, HTTPStatus.ACCEPTED)
                return
            if parsed.path == "/api/open-output":
                output_dir = open_output_dir(
                    str(body.get("output_dir") or "./downloads")
                )
                self._send_json({"path": str(output_dir)})
                return
            self._send_json({"error": "接口不存在"}, HTTPStatus.NOT_FOUND)
        except (ValueError, LinkParseError, DownloadError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            LOGGER.exception("web request failed")
            self._send_json({"error": "处理请求时发生未知错误，请查看日志"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动映存本地 Web 界面")
    parser.add_argument("--port", type=int, default=8000, help="本地端口（默认：8000）")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(OUTPUT_DIR / "douyin_downloader.log")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), WebHandler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"映存 Web 已启动：{url}")
    print("按 Ctrl+C 停止服务")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
