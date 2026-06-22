# 映存 · 抖音公开视频下载工具

一款本地运行的抖音公开视频下载工具，提供 Web 页面、PySide6 桌面窗口和 CLI，用于下载**用户有权保存的公开内容**。项目使用 `yt-dlp` 作为解析和下载核心，`httpx` 仅用于从分享短链按正常 HTTP 重定向获得最终页面地址。

[下载最新 Release](https://github.com/CodeBlueFriend/yingcun-douyin-downloader/releases/latest) · [使用手册](USER_GUIDE.md) · [Release 安装说明](RELEASE.md)

![映存 Web 界面](docs/images/web-interface.jpg)

## Release 安装包

无需安装 Python，前往 [GitHub Releases](https://github.com/CodeBlueFriend/yingcun-douyin-downloader/releases/latest) 下载对应系统版本：

| 系统 | 下载文件 |
| --- | --- |
| Apple Silicon Mac（M 系列芯片） | `Yingcun-macos-arm64.dmg` |
| Intel Mac | `Yingcun-macos-x64.dmg` |
| 64 位 Windows 10/11 | `Yingcun-windows-x64.zip` |

当前稳定版本为 [v0.3.0](https://github.com/CodeBlueFriend/yingcun-douyin-downloader/releases/tag/v0.3.0)。首次运行未签名应用时，系统可能显示安全提示，具体处理方式和 SHA256 校验方法见 [RELEASE.md](RELEASE.md)。

## 功能

- 提供本地 Web 页面、PySide6 桌面界面和 CLI 三种使用方式。
- 支持短链和包含中文文案的完整分享文本。
- 展示标题、作者、封面、时长和可用清晰度。
- 支持最高、1080p、720p、540p 和最低清晰度选择与自动回退。
- 显示下载进度、速度和剩余时间，失败最多尝试 3 次。
- 支持自定义目录和用户主动授权的 cookies 文件。

## 实现方案评估

### A. 基于 yt-dlp（本项目采用）

- 优点：平台适配集中在成熟项目中；格式识别、下载进度、超时和媒体下载行为已有稳定实现；平台页面变化后通常只需升级依赖。
- 缺点：需要持续更新 `yt-dlp`；能否解析仍取决于平台公开页面和平台规则。
- 结论：稳定性更高，维护成本更低，也更容易把功能限定在正常公开访问范围。

### B. 自行使用 requests/httpx 解析页面和接口

- 优点：依赖和行为可完全控制。
- 缺点：页面结构变化频繁，隐藏接口容易失效；维护成本高，并可能滑向签名、风控或访问限制规避，不符合本项目边界。
- 结论：不用于媒体解析。`httpx` 只跟随分享链接的普通重定向。

## 合规边界

- 只用于用户自己创作、已获授权或平台明确允许保存的公开视频。
- 不绕过登录、付费、风控、DRM、私密权限或平台下载限制。
- 不提供批量抓取、接口轰炸或限制规避能力。
- `--cookies` 只接收用户主动提供且有权使用的本地 cookies 文件；程序不会写死、上传或打印 cookies。
- 使用者需遵守抖音服务条款、著作权规则和所在地法律。平台拒绝访问时，工具会停止并给出提示。

## 安装

macOS 或 Windows 均可使用。先安装 Python 3.11 或更高版本，然后在项目目录创建虚拟环境：

```bash
python -m venv .venv
```

macOS：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

平台页面变化可能导致旧版解析失败，可在合规前提下先升级下载核心：

```bash
python -m pip install --upgrade yt-dlp
```

## 桌面版

```bash
python gui.py
```

桌面端提供分享输入、封面信息卡、清晰度选择、实时进度和打开保存目录功能。完整操作步骤见 [USER_GUIDE.md](USER_GUIDE.md)。

## 本地 Web 版（推荐）

```bash
python web_app.py
```

程序只监听 `127.0.0.1:8000` 并自动打开浏览器。页面关闭后，回到终端按 `Ctrl+C` 停止服务。若端口被占用：

```bash
python web_app.py --port 8080
```

Web 版不会把链接或视频上传到第三方服务器。默认保存到项目的 `downloads/` 目录，也可在页面中输入相对路径、绝对路径或 `~/` 路径，并一键用系统文件管理器打开。下载开始后按钮会显示“正在下载”，完成后弹窗提示完整保存位置。

## CLI 使用

下载最高可用清晰度：

```bash
python main.py "https://v.douyin.com/xxxx/" --quality best --output ./downloads
```

直接粘贴包含中文文案的整段分享文本：

```bash
python main.py "好看的视频 https://v.douyin.com/xxxx/ 复制此链接" --quality 1080p
```

只解析信息，不下载：

```bash
python main.py "https://v.douyin.com/xxxx/" --info
```

在用户自行授权的场景传入 Netscape 格式 cookies 文件：

```bash
python main.py "https://www.douyin.com/video/123" --cookies ./cookies.txt
```

`--quality` 可选值：`best`、`1080p`、`720p`、`540p`、`worst`。指定分辨率不存在时，工具优先选择最接近的低一级清晰度并显示提示；如果没有更低清晰度，则选择最低可用项。

文件名格式为 `作者昵称_视频标题_清晰度.mp4`，会自动移除 macOS 和 Windows 不允许的字符。日志写入目标目录的 `douyin_downloader.log`，不会主动记录 cookies 内容。

## 测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

基础测试覆盖分享文本 URL 提取、非法域名拒绝、最高/最低清晰度选择和缺失清晰度回退。测试不请求真实抖音页面。

## 常见问题

- **链接无法访问**：确认链接仍有效，并检查网络；短链跳转到非抖音域名时程序会拒绝处理。
- **无法解析或没有格式**：视频可能已删除、不是公开内容、受地区限制，或平台不允许下载。工具不会尝试绕过。
- **解析突然失效**：先升级 `yt-dlp`。若平台仍拒绝访问，请尊重该限制。
- **cookies 报错**：确认文件存在且为 Netscape cookies 格式；不要使用不属于自己的账号凭据。
