# JMComic Portable 🚀

[中文](README.md) | [English](README_EN.md)

> [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) 的一键启动、免安装 Windows 便携版。

解压即用，双击 `start.bat` 启动——无需安装 Python，无需下载依赖，无需任何配置。所有运行环境已打包在内。

## 致谢

本项目基于 [**JMComic-Crawler-Python**](https://github.com/hect0x7/JMComic-Crawler-Python) 制作，原作者 [@hect0x7](https://github.com/hect0x7)，采用 MIT 开源协议。

核心 JMComic API 库的全部功劳归于原作者。本便携版仅在其基础上添加了自包含的 Windows 启动器，内置 Python 运行时和预下载的依赖包。

## 特性

- 🔌 **完全离线部署** — 内置 Python 3.12 运行时 + 全部依赖（约 27 MB）
- 🖱️ **一键启动** — 双击 `start.bat`，自动打开浏览器
- 🌐 **Web 界面** — 搜索、浏览排行榜、管理收藏、下载漫画
- 📦 **无需安装** — 解压即用，U 盘随身携带

## 快速开始

1. 从 [Releases](../../releases) 下载 `JMComic-Portable-Windows.zip`
2. 解压到任意位置（桌面、U 盘等）
3. 双击 `start.bat`
4. 首次启动约 10-30 秒完成初始化（完全离线，无需联网）
5. 浏览器自动打开 `http://127.0.0.1:5000`

## 使用技巧

- **代理设置**：如果禁漫在你所在的地区被屏蔽，在 Web 界面的「设置」中配置代理
- **下载位置**：漫画保存在 `start.bat` 旁边的 `downloads` 文件夹中
- **停止服务**：在控制台窗口按 `Ctrl+C`，或直接关闭窗口
- **重置环境**：删除 `python`、`downloads` 文件夹和 `web/user_settings.json`，重新运行 `start.bat`

## 目录结构

```
JMComic-Portable/
├── start.bat              ← 双击启动
├── python-embed.zip       ← Python 3.12 运行时（首次运行自动解压）
├── packages/              ← 预下载的依赖包（离线安装）
├── src/jmcomic/           ← JMComic API 库（来自原项目）
├── web/                   ← Flask Web 界面
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   ├── static/
│   └── templates/
└── downloads/             ← 运行时自动创建（存放下载的漫画）
```

## 开源协议

本项目与原项目 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) 使用相同的 [MIT License](LICENSE)。

Copyright (c) 2023 hect0x7 — 原 JMComic-Crawler-Python 项目

## 免责声明

本软件仅提供技术工具，不包含任何内容。用户使用本软件访问的任何网站、下载的任何内容均与开发者无关。

- 本软件为**学习交流用途**，请勿用于商业或非法目的
- 使用者应**自行遵守**所在地区的法律法规
- 本软件**不提供、不存储、不传播**任何漫画内容
- 开发者**不负责**用户使用本软件获取的任何第三方内容
- 禁漫天堂（JMComic）是第三方网站，与本项目**无任何关联**
- 使用本软件即表示你已**年满 18 周岁**且同意承担全部责任
