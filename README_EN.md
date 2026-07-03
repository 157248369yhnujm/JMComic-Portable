# JMComic Portable 🚀

[中文](README.md) | [English](README_EN.md)

> One-click, offline-ready portable distribution of [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python).

Just **unzip and double-click `start.bat`** — no Python installation, no dependency downloads, no configuration needed. Everything is bundled.

## Credits

This project is based on **[JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python)** by [@hect0x7](https://github.com/hect0x7), licensed under the MIT License.

All credit for the core JMComic API library goes to the original author. This portable distribution only adds a self-contained Windows launcher with an embedded Python runtime and pre-downloaded dependencies.

## Features

- 🔌 **Fully offline setup** — Embedded Python 3.12 + all dependencies bundled (~27 MB)
- 🖱️ **One-click launch** — Double-click `start.bat`, browser opens automatically
- 🌐 **Web UI** — Search, browse rankings, manage favorites, and download comics
- 📦 **No installation** — Just extract the zip and run

## Quick Start

1. Download `JMComic-Portable-Windows.zip` from [Releases](../../releases)
2. Extract anywhere (Desktop, USB drive, etc.)
3. Double-click `start.bat`
4. First run takes ~10-30 seconds to set up (fully offline)
5. Browser opens to `http://127.0.0.1:5000`

## Usage Tips

- **Proxy**: If JMComic is blocked in your region, go to Settings in the Web UI and configure a proxy
- **Downloads**: Saved to the `downloads/` folder next to `start.bat`
- **Stop**: Press `Ctrl+C` in the console window, or just close it
- **Reset**: Delete `python/`, `downloads/`, and `web/user_settings.json`, then re-run `start.bat`

## Structure

```
JMComic-Portable/
├── start.bat              ← Double-click to launch
├── python-embed.zip       ← Python 3.12 runtime (auto-extracted on first run)
├── packages/              ← Pre-downloaded wheels (offline install)
├── src/jmcomic/           ← JMComic API library (from original project)
├── web/                   ← Flask Web UI
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   ├── static/
│   └── templates/
└── downloads/             ← Created at runtime (your downloaded comics)
```

## License

This project uses the same [MIT License](LICENSE) as the original [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python).

Copyright (c) 2023 hect0x7 — Original JMComic-Crawler-Python project

## Disclaimer

This software is a technical tool only. It does not contain, host, or distribute any content. The developer is not responsible for any third-party content accessed through this software.

- This software is for **educational and personal use only**. Commercial or illegal use is strictly prohibited
- Users must **comply with all applicable laws** in their jurisdiction
- This software **does not provide, store, or distribute** any comic content
- The developer **assumes no liability** for third-party content obtained via this software
- JMComic (禁漫天堂) is a third-party website **not affiliated** with this project
- By using this software, you confirm you are **at least 18 years of age** and accept full responsibility
