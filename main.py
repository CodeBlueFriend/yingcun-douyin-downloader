from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from downloader.download import DouyinDownloader, DownloadError
from downloader.parser import LinkParseError, extract_share_url, resolve_share_url
from downloader.quality import Quality
from downloader.utils import configure_logging, format_duration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="下载您有权保存的抖音公开视频（不绕过平台限制）"
    )
    parser.add_argument("share_text", help="抖音分享链接或包含链接的分享文本")
    parser.add_argument(
        "--quality",
        choices=[quality.value for quality in Quality],
        default=Quality.BEST.value,
        help="下载清晰度（默认：best）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("downloads"),
        help="保存目录（默认：./downloads）",
    )
    parser.add_argument("--info", action="store_true", help="只显示视频信息，不下载")
    parser.add_argument(
        "--cookies",
        type=Path,
        help="用户自行授权导出的 Netscape 格式 cookies 文件",
    )
    return parser


def print_info(info: object) -> None:
    from downloader.download import VideoInfo

    if not isinstance(info, VideoInfo):
        raise TypeError("unexpected video info type")
    print(f"标题：{info.title}")
    print(f"作者：{info.author}")
    print(f"时长：{format_duration(info.duration)}")
    print(f"封面：{info.thumbnail or '无'}")
    qualities = ", ".join(f"{item.height}p" for item in info.formats)
    print(f"可用清晰度：{qualities or '未识别'}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output: Path = args.output.expanduser()
    configure_logging(output / "douyin_downloader.log")

    try:
        if args.cookies is not None and not args.cookies.expanduser().is_file():
            raise DownloadError("cookies 文件不存在或不是文件")
        share_url = extract_share_url(args.share_text)
        resolved_url = resolve_share_url(share_url)
        client = DouyinDownloader(
            output_dir=output,
            cookies_file=args.cookies.expanduser() if args.cookies else None,
        )
        info = client.fetch_info(resolved_url)
        print_info(info)
        if args.info:
            return 0
        result = client.download(info, Quality(args.quality))
        if result.notice:
            print(f"提示：{result.notice}")
        print(f"下载完成：{result.path}")
        return 0
    except (LinkParseError, DownloadError) as exc:
        logging.getLogger(__name__).error("操作失败：%s", exc)
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
