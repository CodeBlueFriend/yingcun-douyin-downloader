from __future__ import annotations

import pytest

from downloader.parser import LinkParseError, extract_share_url


@pytest.mark.parametrize(
    ("share_text", "expected"),
    [
        ("https://v.douyin.com/abc123/", "https://v.douyin.com/abc123/"),
        (
            "看看这个作品！ https://v.douyin.com/xyz987/ 复制此链接打开抖音",
            "https://v.douyin.com/xyz987/",
        ),
        (
            "分享：https://www.douyin.com/video/1234567890。",
            "https://www.douyin.com/video/1234567890",
        ),
    ],
)
def test_extract_share_url(share_text: str, expected: str) -> None:
    assert extract_share_url(share_text) == expected


def test_extract_uses_first_douyin_url() -> None:
    text = "https://example.com/no https://v.douyin.com/yes/"
    assert extract_share_url(text) == "https://v.douyin.com/yes/"


@pytest.mark.parametrize(
    "share_text",
    ["没有链接", "https://example.com/video/1", "ftp://v.douyin.com/abc"],
)
def test_extract_rejects_missing_or_unsupported_url(share_text: str) -> None:
    with pytest.raises(LinkParseError):
        extract_share_url(share_text)
