========================================
  JMComic Downloader - Portable Edition
========================================

This is a self-contained, portable package. No installation required.
Everything you need is bundled inside this folder.

HOW TO USE
----------

1. Double-click "start.bat" to launch.
2. On the first run, the script will extract the Python runtime and
   install dependencies. This takes about 10-30 seconds and is fully
   offline - no internet connection is needed.
3. Your web browser will open automatically to http://127.0.0.1:5000
4. Use the web interface to search, browse, and download comics.
5. Press Ctrl+C in the console window to stop the server.

TIPS
----

* The console window shows server status. Keep it open while using
  the web interface. Closing it stops the server.
* Downloaded comics are saved in the "downloads" folder next to
  this README.
* Configure your proxy in the web UI under Settings if you need one.
* All settings are saved locally in this folder. Nothing is sent
  to any external server.
* To reset everything, delete the "python", "downloads", and
  "web/user_settings.json" files/folders, then re-run start.bat.

TROUBLESHOOTING
---------------

Q: Browser opens but shows "connection refused"?
A: Wait a moment and refresh. The server takes 1-2 seconds to boot.
   If it still fails, check the console window for error messages.

Q: Can't access JMComic?
A: JMComic may be blocked in your region. Go to the web UI Settings
   page and configure a proxy (e.g. http://127.0.0.1:7890).

Q: Start.bat says "Python runtime" error?
A: Make sure the file "python-embed.zip" is in the same folder as
   start.bat. Re-extract the original zip package if it's missing.

FILES INCLUDED
--------------

start.bat           - Main launcher (double-click to run)
python-embed.zip    - Python 3.12 runtime for Windows (bundled)
packages/           - Python dependencies (pre-downloaded, offline)
src/jmcomic/        - JMComic API library
web/                - Web UI application
get-pip.py          - Reserved for advanced troubleshooting
