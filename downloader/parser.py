from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,!?;:，。！？；：、)]}）】》"
ALLOWED_HOSTS = ("douyin.com",)


class LinkParseError(ValueError):
    """Raised when a usable public Douyin URL cannot be obtained."""


def _is_douyin_host(host: str | None) -> bool:
    normalized = (host or "").lower().rstrip(".")
    return any(
        normalized == suffix or normalized.endswith(f".{suffix}")
        for suffix in ALLOWED_HOSTS
    )


def extract_share_url(share_text: str) -> str:
    """Extract the first valid Douyin HTTP URL from a share message."""
    for match in URL_PATTERN.finditer(share_text):
        candidate = match.group(0).rstrip(TRAILING_PUNCTUATION)
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"} and _is_douyin_host(parsed.hostname):
            return candidate
    raise LinkParseError("未在分享文本中找到有效的抖音链接")


def resolve_share_url(url: str, timeout: float = 15.0) -> str:
    """Follow ordinary HTTP redirects and return the final Douyin page URL."""
    if not _is_douyin_host(urlparse(url).hostname):
        raise LinkParseError("仅支持 douyin.com 域名下的公开分享链接")
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DouyinDownloader/1.0)"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LinkParseError("分享链接无法正常访问，请检查链接或稍后重试") from exc

    final_url = str(response.url)
    if not _is_douyin_host(response.url.host):
        raise LinkParseError("分享链接重定向到了非抖音站点，已停止处理")
    return final_url
