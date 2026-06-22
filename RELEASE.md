# 映存 Release 使用说明

GitHub Release 提供无需安装 Python 的版本。应用只在本机启动 Web 服务，浏览器中的链接、路径和下载任务不会发送到第三方服务器。

## 下载对应版本

| 文件 | 适用系统 |
| --- | --- |
| `Yingcun-macos-arm64.dmg` | Apple Silicon Mac（M 系列芯片） |
| `Yingcun-macos-x64.dmg` | Intel Mac |
| `Yingcun-windows-x64.zip` | 64 位 Windows 10/11 |

`.zip` 是备用压缩包，`SHA256SUMS.txt` 用于校验文件完整性。

## macOS

1. 打开对应架构的 `.dmg`。
2. 将 `Yingcun.app` 拖入 Applications。
3. 双击启动，应用会打开默认浏览器。
4. 视频默认保存到 `~/Downloads/Yingcun`，也可在页面修改。
5. 使用结束后点击页面底部“退出本地服务”。

当前自动构建未使用 Apple Developer 证书签名。首次运行若被 macOS 拦截，可在 Finder 中右键应用并选择“打开”，然后在系统确认框中再次选择“打开”。

## Windows

1. 解压 `Yingcun-windows-x64.zip`，不要只单独复制其中的 `.exe`。
2. 双击文件夹中的 `Yingcun.exe`。
3. 应用会打开默认浏览器，默认保存到用户下载目录下的 `Yingcun` 文件夹。
4. 使用结束后点击页面底部“退出本地服务”。

当前自动构建未购买代码签名证书，Windows SmartScreen 可能显示“未知发布者”。请只从本项目 GitHub Release 下载，并用 `SHA256SUMS.txt` 校验文件。

## 创建新版本

维护者更新版本号并推送标签后，GitHub Actions 会构建三个平台包并创建 Release：

```bash
git tag v0.3.0
git push origin v0.3.0
```

也可在 GitHub Actions 中手动运行 `release` 工作流，只生成可下载的构建产物，不创建正式 Release。
