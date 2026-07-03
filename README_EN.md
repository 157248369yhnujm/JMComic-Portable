# JMComic Portable 🚀

[中文](README.md) | [English](README_EN.md)

> A portable, offline-ready Windows launcher for [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python). Unzip and run — no setup needed.

Bundles Python 3.12 runtime and all dependencies. First launch is fully offline — no internet required for setup. Runs from anywhere, including USB drives.

## Credits

Based on [**JMComic-Crawler-Python**](https://github.com/hect0x7/JMComic-Crawler-Python) by [@hect0x7](https://github.com/hect0x7), under the same MIT License.

All credit for the core API library belongs to the original author. This distribution only adds a self-contained Windows runtime for one-click usage.

## Features

| Module | Description |
|--------|-------------|
| 🔍 Search | Keyword search with advanced syntax (AND/OR/NOT) |
| 📊 Rankings | Daily, weekly, monthly, all-time, latest, most-liked |
| ❤️ Favorites | Login and sync your account favorites |
| 📥 Downloader | Multi-threaded downloads, queue management, ZIP export |
| 📂 Local Library | **Downloaded comics saved locally — reread without re-downloading** |
| 📖 Reader | Okuma reader with single/double-page mode |
| ⚙️ Settings | Proxy, thread count, download path, and more |

## Quick Start

1. Download `JMComic-Portable-Windows.zip` from [Releases](../../releases)
2. Extract anywhere (Desktop, USB drive, etc.)
3. Double-click `start.bat`
4. First run takes ~10-30 seconds (offline), instant afterwards

## Directory Structure

```
JMComic-Portable/
├── start.bat              ← Double-click to launch
├── python-embed.zip       ← Python 3.12 runtime (auto-extracted)
├── packages/              ← Pre-downloaded wheels (offline)
├── src/jmcomic/           ← JMComic API library
├── web/                   ← Web UI
└── downloads/             ← Created at runtime (saved comics)
```

## Disclaimer

- This is a **technical tool** — it does not contain, host, or distribute any content
- For **educational and personal use only**; commercial or illegal use is prohibited
- Users are **solely responsible** for complying with applicable laws
- JMComic is a third-party website **not affiliated** with this project
- You must be **at least 18 years of age** to use this software
- All data is stored **locally only** — nothing is uploaded anywhere

## License

Same [MIT License](LICENSE) as [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python).

Copyright (c) 2023 hect0x7
