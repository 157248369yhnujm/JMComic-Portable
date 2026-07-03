# JMComic Portable 🚀

[中文](README.md) | [English](README_EN.md)

> [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) 的 Windows 免安装便携版——解压即用，双击启动。

内置 Python 运行时 + 全部依赖，首次启动完全离线，无需联网下载任何东西。U 盘带走，插上就能用。

## 致谢

本项目基于 [**JMComic-Crawler-Python**](https://github.com/hect0x7/JMComic-Crawler-Python)（作者 [@hect0x7](https://github.com/hect0x7)）制作，沿用原项目 MIT 协议。

核心 API 库的全部功劳归于原作者。本便携版仅在其基础上打包了 Windows 运行环境，方便不懂命令行的用户开箱即用。

## 功能

| 模块 | 说明 |
|------|------|
| 🔍 搜索 | 关键字搜索，支持高级语法（AND/OR/NOT） |
| 📊 排行榜 | 日榜、周榜、月榜、总榜、最新、最多爱心 |
| ❤️ 收藏夹 | 登录禁漫账号，浏览和添加收藏 |
| 📥 下载器 | 多线程下载，队列管理，支持导出为 ZIP |
| 📂 本地库 | **下载过的漫画本地保存，再次阅读不耗流量，无需重新拉取** |
| 📖 阅读器 | Okuma 阅读器，双页/单页模式，自适应屏幕 |
| ⚙️ 设置 | 代理配置、线程数、下载目录等 |

## 快速开始

1. 从 [Releases](../../releases) 下载 `JMComic-Portable-Windows.zip`
2. 解压到任意位置
3. 双击 `start.bat`
4. 首次启动约 10-30 秒（完全离线），之后秒开

## 目录结构

```
JMComic-Portable/
├── start.bat              ← 双击启动
├── python-embed.zip       ← Python 3.12 运行时（首次自动解压）
├── packages/              ← 预下载依赖（离线安装）
├── src/jmcomic/           ← JMComic API 库
├── web/                   ← Web 界面
└── downloads/             ← 运行时创建（下载的漫画存这里）
```

## 免责声明

- 本软件为**技术工具**，不包含、不提供、不存储任何漫画内容
- **仅供学习交流**，严禁用于商业或违法用途
- 使用者须自行遵守所在地法律，**自行承担全部责任**
- 禁漫天堂是第三方网站，与本项目**无任何关联**
- 使用前请确认你**已年满 18 周岁**
- 所有数据仅存储在本地，**不会上传到任何服务器**

## 开源协议

与原项目 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) 相同，使用 [MIT License](LICENSE)。

Copyright (c) 2023 hect0x7
