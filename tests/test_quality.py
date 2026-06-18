from __future__ import annotations

import pytest

from downloader.quality import Quality, VideoFormat, select_quality


FORMATS = (
    VideoFormat("540", 540, bitrate=700),
    VideoFormat("720-low", 720, bitrate=900),
    VideoFormat("720-high", 720, bitrate=1200),
    VideoFormat("1080", 1080, bitrate=2200),
)


def test_best_selects_highest_resolution() -> None:
    selection = select_quality(FORMATS, Quality.BEST)
    assert selection.video_format.format_id == "1080"
    assert selection.notice is None


def test_worst_selects_lowest_resolution() -> None:
    assert select_quality(FORMATS, Quality.WORST).video_format.height == 540


def test_exact_quality_prefers_higher_bitrate() -> None:
    selection = select_quality(FORMATS, Quality.P720)
    assert selection.video_format.format_id == "720-high"
    assert selection.notice is None


def test_missing_quality_falls_back_to_lower_level() -> None:
    selection = select_quality(FORMATS, Quality.P1080)
    assert selection.video_format.height == 1080

    without_1080 = FORMATS[:-1]
    fallback = select_quality(without_1080, Quality.P1080)
    assert fallback.video_format.height == 720
    assert fallback.notice == "没有 1080p，已自动选择 720p"


def test_no_lower_quality_uses_lowest_available() -> None:
    formats = (VideoFormat("4k", 2160),)
    selection = select_quality(formats, Quality.P540)
    assert selection.video_format.height == 2160
    assert selection.notice is not None


def test_empty_formats_is_rejected() -> None:
    with pytest.raises(ValueError, match="没有可下载"):
        select_quality([], Quality.BEST)
