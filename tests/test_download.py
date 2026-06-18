from __future__ import annotations

from pathlib import Path
from typing import Any

from downloader.download import DouyinDownloader, VideoInfo
from downloader.quality import Quality, VideoFormat


def test_download_reuses_extracted_info(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[tuple[dict[str, Any], bool]] = []
    output_file = tmp_path / "author_title_720p.mp4"

    class FakeYoutubeDL:
        def __init__(self, options: dict[str, Any]) -> None:
            self.options = options

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def process_ie_result(
            self, source_info: dict[str, Any], download: bool
        ) -> dict[str, Any]:
            calls.append((source_info, download))
            output_file.touch()
            return source_info

        def download(self, urls: list[str]) -> None:
            raise AssertionError("download(url) would re-run the extractor")

    monkeypatch.setattr("downloader.download.YoutubeDL", FakeYoutubeDL)
    info = VideoInfo(
        webpage_url="https://www.douyin.com/video/123",
        title="title",
        author="author",
        thumbnail=None,
        duration=1.0,
        formats=(VideoFormat("format-720", 720),),
        source_info={"id": "123", "formats": [{"format_id": "format-720"}]},
    )

    result = DouyinDownloader(tmp_path).download(info, Quality.BEST)

    assert result.path == output_file
    assert calls == [(info.source_info, True)]
