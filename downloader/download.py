from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from tqdm import tqdm
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from .quality import Quality, VideoFormat, select_quality
from .utils import sanitize_filename

LOGGER = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    """A user-facing metadata or download failure."""


@dataclass(frozen=True, slots=True)
class VideoInfo:
    webpage_url: str
    title: str
    author: str
    thumbnail: str | None
    duration: float | None
    formats: tuple[VideoFormat, ...]
    source_info: dict[str, Any] = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    quality: VideoFormat
    notice: str | None


class ProgressDisplay:
    def __init__(self) -> None:
        self._bar: tqdm[Any] | None = None

    def __call__(self, status: Mapping[str, Any]) -> None:
        state = status.get("status")
        if state == "downloading":
            total = status.get("total_bytes") or status.get("total_bytes_estimate")
            downloaded = int(status.get("downloaded_bytes") or 0)
            if self._bar is None:
                self._bar = tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="下载中",
                    dynamic_ncols=True,
                )
            if total and self._bar.total != total:
                self._bar.total = total
            self._bar.update(max(0, downloaded - self._bar.n))
            speed = status.get("speed")
            eta = status.get("eta")
            self._bar.set_postfix(
                speed=f"{speed / 1024 / 1024:.2f} MiB/s" if speed else "--",
                eta=f"{int(eta)}s" if eta is not None else "--",
            )
        elif state == "finished" and self._bar is not None:
            self._bar.close()
            self._bar = None

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()
            self._bar = None


class DouyinDownloader:
    def __init__(self, output_dir: Path, cookies_file: Path | None = None) -> None:
        self.output_dir = output_dir.resolve()
        self.cookies_file = cookies_file.resolve() if cookies_file else None

    def _base_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "socket_timeout": 20,
        }
        if self.cookies_file:
            options["cookiefile"] = str(self.cookies_file)
        return options

    def fetch_info(self, webpage_url: str) -> VideoInfo:
        try:
            with YoutubeDL(self._base_options()) as ydl:
                raw = ydl.extract_info(webpage_url, download=False)
        except YtDlpDownloadError as exc:
            LOGGER.exception("yt-dlp metadata extraction failed")
            raise DownloadError(
                "无法解析该视频。它可能已删除、不是公开内容，或平台不允许访问"
            ) from exc
        if not isinstance(raw, dict):
            raise DownloadError("未获取到有效的视频信息")

        formats = self._parse_formats(raw.get("formats") or [])
        if not formats:
            raise DownloadError("未找到平台允许下载的视频格式")
        return VideoInfo(
            webpage_url=str(raw.get("webpage_url") or webpage_url),
            title=str(raw.get("title") or raw.get("description") or "未命名"),
            author=str(raw.get("uploader") or raw.get("creator") or "未知作者"),
            thumbnail=str(raw["thumbnail"]) if raw.get("thumbnail") else None,
            duration=float(raw["duration"]) if raw.get("duration") is not None else None,
            formats=formats,
            source_info=raw,
        )

    @staticmethod
    def _parse_formats(raw_formats: list[dict[str, Any]]) -> tuple[VideoFormat, ...]:
        best_by_height: dict[int, VideoFormat] = {}
        for item in raw_formats:
            height = item.get("height")
            format_id = item.get("format_id")
            if not isinstance(height, (int, float)) or not format_id:
                continue
            if item.get("vcodec") == "none":
                continue
            video_format = VideoFormat(
                format_id=str(format_id),
                height=int(height),
                width=int(item["width"]) if item.get("width") else None,
                bitrate=float(item["tbr"]) if item.get("tbr") else None,
                extension=str(item.get("ext") or "mp4"),
            )
            previous = best_by_height.get(video_format.height)
            if previous is None or (video_format.bitrate or 0) > (previous.bitrate or 0):
                best_by_height[video_format.height] = video_format
        return tuple(best_by_height[key] for key in sorted(best_by_height))

    def download(
        self,
        info: VideoInfo,
        quality: Quality,
        progress_hook: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> DownloadResult:
        selection = select_quality(info.formats, quality)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        quality_label = f"{selection.video_format.height}p"
        filename = "_".join(
            (
                sanitize_filename(info.author, 60),
                sanitize_filename(info.title, 100),
                quality_label,
            )
        )
        output_template = self.output_dir / f"{filename}.%(ext)s"
        progress = ProgressDisplay()
        options = self._base_options()
        progress_hooks: list[Callable[[Mapping[str, Any]], None]] = (
            [progress_hook] if progress_hook is not None else [progress]
        )
        options.update(
            {
                "format": selection.video_format.format_id,
                "outtmpl": str(output_template),
                "progress_hooks": progress_hooks,
                # This class owns the three-attempt policy below.
                "retries": 0,
                "fragment_retries": 3,
                "overwrites": False,
            }
        )

        try:
            last_error: Exception | None = None
            for attempt in range(1, 4):
                try:
                    with YoutubeDL(options) as ydl:
                        # Reuse the signed format data from fetch_info. Calling
                        # download([url]) here would run the extractor twice and
                        # can stall on the second Douyin page request.
                        ydl.process_ie_result(info.source_info.copy(), download=True)
                    break
                except YtDlpDownloadError as exc:
                    last_error = exc
                    LOGGER.warning("download attempt %d/3 failed", attempt, exc_info=True)
                    if attempt < 3:
                        time.sleep(attempt)
            else:
                raise DownloadError("下载失败，重试 3 次后仍无法完成") from last_error
        finally:
            progress.close()

        expected = output_template.with_suffix(f".{selection.video_format.extension}")
        matches = sorted(self.output_dir.glob(f"{filename}.*"))
        path = expected if expected.exists() else (matches[0] if matches else expected)
        if not path.is_file():
            raise DownloadError("下载过程结束，但未找到输出文件，请查看日志排查")
        return DownloadResult(path, selection.video_format, selection.notice)
