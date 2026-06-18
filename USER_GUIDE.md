# 映存使用手册

“映存”是一款用于保存**你有权下载的抖音公开视频**的桌面工具，同时保留命令行模式。本文适用于 Python 3.11 及以上版本，支持 macOS 和 Windows。

## 1. 使用边界

使用前请确认视频由你创作、已获得作者授权，或平台明确允许保存。本工具不会绕过登录、付费、私密权限、风控、DRM 或其他平台限制，也不提供批量抓取功能。平台拒绝访问时应停止操作。

## 2. 安装

在项目目录打开终端。

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 3. 启动桌面版

macOS：

```bash
source .venv/bin/activate
python gui.py
```

Windows：

```powershell
.venv\Scripts\Activate.ps1
python gui.py
```

也可安装为本地命令：

```bash
python -m pip install -e .
yingcun
```

## 4. 桌面版操作流程

1. 从抖音复制公开视频的分享链接或完整分享文案。
2. 将内容粘贴到“分享内容”输入框。
3. 点击“选择目录”设置视频与日志保存位置。
4. 点击“解析视频”，等待标题、作者、封面、时长和可用清晰度显示。
5. 在“目标清晰度”中选择原画、1080p、720p、540p 或最低清晰度。
6. 点击“开始下载”，通过进度条查看速度和剩余时间。
7. 完成后点击“打开保存目录”查看视频。

如果目标清晰度不存在，程序会选择最接近的低一级清晰度；若没有更低档，则使用最低可用档位并给出提示。

## 5. Cookies（可选）

仅在你自己的授权场景中使用“授权 Cookies（可选）”。请选择 Netscape 格式的本地 cookies 文本文件。程序不会将 cookie 内容写死在代码中，也不会主动打印其内容。

Cookies 不能用于绕过私密权限、付费或平台限制。若平台仍拒绝访问，请停止处理。

## 6. 命令行模式

最高可用清晰度：

```bash
python main.py "https://v.douyin.com/xxxx/" --quality best --output ./downloads
```

只查看视频信息：

```bash
python main.py "包含链接的完整分享文案" --info
```

可用参数：

| 参数 | 说明 |
| --- | --- |
| `--quality` | `best`、`1080p`、`720p`、`540p`、`worst` |
| `--output` | 自定义保存目录 |
| `--info` | 只解析，不下载 |
| `--cookies` | 用户主动提供的 Netscape cookies 文件 |

## 7. 文件与日志

视频命名格式：

```text
作者昵称_视频标题_清晰度.mp4
```

日志文件位于保存目录下的 `douyin_downloader.log`。反馈问题时可以提供日志，但提交前仍建议检查并删除不希望公开的信息。

## 8. 常见问题

### 一直显示“正在解析”

抖音页面解析可能需要数十秒。确认网络可正常访问该公开页面，并保持 `yt-dlp` 为较新版本：

```bash
python -m pip install --upgrade yt-dlp
```

### 链接可以打开但不能下载

视频可能存在地区限制、已删除、转为非公开，或平台不允许下载。本工具不会规避这些限制。

### GUI 无法启动

确认虚拟环境已激活，并重新安装依赖：

```bash
python -m pip install -r requirements.txt
```

### 下载完成但无法播放

先确认文件大小不是 0。播放器兼容性不足时可尝试 VLC 等支持常见 MP4 编码的播放器；不要用转码方式处理受 DRM 保护的内容。

## 9. 运行测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

自动测试不访问真实抖音页面。
