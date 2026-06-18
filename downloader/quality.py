from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Quality(str, Enum):
    BEST = "best"
    P1080 = "1080p"
    P720 = "720p"
    P540 = "540p"
    WORST = "worst"


@dataclass(frozen=True, slots=True)
class VideoFormat:
    format_id: str
    height: int
    width: int | None = None
    bitrate: float | None = None
    extension: str = "mp4"


@dataclass(frozen=True, slots=True)
class QualitySelection:
    video_format: VideoFormat
    requested: Quality
    notice: str | None = None


def select_quality(
    formats: Iterable[VideoFormat], requested: Quality
) -> QualitySelection:
    """Choose best/worst or the closest available height not above the target."""
    available = list(formats)
    if not available:
        raise ValueError("没有可下载的视频清晰度")

    ranked = sorted(
        available,
        key=lambda item: (item.height, item.bitrate or 0.0),
    )
    if requested is Quality.BEST:
        return QualitySelection(ranked[-1], requested)
    if requested is Quality.WORST:
        return QualitySelection(ranked[0], requested)

    target = int(requested.value.removesuffix("p"))
    lower_or_equal = [item for item in ranked if item.height <= target]
    selected = lower_or_equal[-1] if lower_or_equal else ranked[0]
    notice = None
    if selected.height != target:
        notice = f"没有 {target}p，已自动选择 {selected.height}p"
    return QualitySelection(selected, requested, notice)
