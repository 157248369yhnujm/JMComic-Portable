"""
JMComic Web UI — Flask 应用主入口
启动方法: python app.py
"""

import os
import sys
import threading
import logging

# 配置日志（确保后台线程的日志能输出到控制台）
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)

# 路径初始化
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flask import Flask, send_from_directory
from config import SERVER_HOST, SERVER_PORT, SETTINGS_FILE
from option_builder import load_settings


def _prefetch_cdn_domain(app):
    """后台线程：预加载 CDN 域名"""
    try:
        from jmcomic import create_option_by_str
        from option_builder import build_option_yaml
        settings = load_settings(SETTINGS_FILE)
        yaml_str = build_option_yaml(settings)
        option = create_option_by_str(yaml_str)
        client = option.new_jm_client()

        # 用常见 ID 获取
        for test_id in ['123456', '1', '100']:
            try:
                album = client.get_album_detail(test_id)
                if album and hasattr(album, 'episode_list') and album.episode_list:
                    first_ep = album.episode_list[0]
                    photo_id = first_ep[0] if isinstance(first_ep, (list, tuple)) else first_ep.get('photo_id', '')
                    if photo_id:
                        photo = client.get_photo_detail(photo_id, fetch_album=False)
                        if photo:
                            domain = getattr(photo, 'data_original_domain', None)
                            if domain:
                                app.config['cdn_domain'] = domain
                                app.config['jm_client'] = client
                                print(f"[启动] CDN 域名已获取: {domain}")
                                return
            except Exception:
                continue
    except Exception as e:
        print(f"[启动] CDN 域名预加载失败: {e}")


def create_app():
    """Flask 应用工厂"""
    # 确保运行时必要的目录存在
    settings = load_settings(SETTINGS_FILE)
    for d in (settings.get('download_dir', ''),
              os.path.join(os.path.dirname(__file__), 'cover_cache')):
        if d:
            os.makedirs(d, exist_ok=True)

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )

    # 初始化下载管理器
    from download_manager import DownloadManager

    def get_current_settings():
        return load_settings(SETTINGS_FILE)

    app.config['download_manager'] = DownloadManager(get_current_settings)
    app.config['jm_client'] = None
    app.config['jm_option'] = None
    app.config['cdn_domain'] = None

    # 注册 API Blueprints
    from routes.api_search import search_bp
    from routes.api_album import album_bp
    from routes.api_download import download_bp
    from routes.api_ranking import ranking_bp
    from routes.api_favorites import favorites_bp
    from routes.api_settings import settings_bp
    from routes.api_cover import cover_bp
    from routes.api_local import local_bp

    app.register_blueprint(search_bp)
    app.register_blueprint(album_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(ranking_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(cover_bp)
    app.register_blueprint(local_bp)

    # 根路由
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

    # -- Okuma-Reader 集成 --
    @app.route('/api/okuma/config.json')
    def okuma_library_config():
        """Okuma library config: 所有可用的 titles"""
        from flask import jsonify, request
        # 返回当前请求的 title（如果知道的话），最少要包含正在阅读的 title
        # Okuma 用这个来验证 title 是否存在
        title = request.args.get('title', '')
        titles = [title] if title else []
        return jsonify({"titles": titles})

    @app.route('/reader')
    def reader_page():
        from flask import render_template, request, make_response
        album_id = request.args.get('title', '')
        photo_id = request.args.get('volume', '')
        album_name = f'JM{album_id}'
        if album_id:
            try:
                from option_builder import load_settings, build_option
                from config import SETTINGS_FILE
                settings = load_settings(SETTINGS_FILE)
                option = build_option(settings)
                client = option.new_jm_client()
                album = client.get_album_detail(album_id)
                if album:
                    album_name = getattr(album, 'name', album_name) or album_name
            except Exception:
                pass
        resp = make_response(render_template('reader.html', album_name=album_name, album_id=album_id, photo_id=photo_id))
        # 阅读页内联脚本改动较频繁，禁缓存确保浏览器始终拿到最新版
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

    @app.route('/api/okuma/<album_id>/config.json')
    def okuma_title_config(album_id):
        """Okuma TCONFIG: 标题级别配置"""
        from flask import jsonify
        try:
            # 读取该 album 的所有章节
            from option_builder import load_settings, build_option
            from config import SETTINGS_FILE
            settings = load_settings(SETTINGS_FILE)
            option = build_option(settings)
            client = option.new_jm_client()
            album = client.get_album_detail(album_id)
            if not album:
                return jsonify({"error": "Album not found"}), 404

            # 章节作为 volumes
            episodes = getattr(album, 'episode_list', []) or []
            if not episodes:
                return jsonify({"error": "No episodes"}), 404

            volumes = []
            for ep in episodes:
                pid = ep[0] if isinstance(ep, (list, tuple)) else ep.get('photo_id', '')
                if pid:
                    volumes.append(str(pid))

            return jsonify({
                "fileExtension": ".webp",
                "volumes": volumes,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/okuma/<album_id>/<photo_id>/config.json')
    def okuma_volume_config(album_id, photo_id):
        """Okuma VCONFIG: 卷级别配置（页数、章节书签）"""
        from flask import jsonify
        try:
            from option_builder import load_settings, build_option
            from config import SETTINGS_FILE
            settings = load_settings(SETTINGS_FILE)
            option = build_option(settings)
            client = option.new_jm_client()
            photo = client.get_photo_detail(photo_id, fetch_album=False)
            if not photo:
                return jsonify({"error": "Photo not found"}), 404

            page_arr = getattr(photo, 'page_arr', []) or []
            return jsonify({
                "numPages": len(page_arr),
                "bookmarks": [],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # 后台预加载 CDN 域名 + 自动登录
    threading.Thread(target=_prefetch_cdn_domain, args=(app,), daemon=True).start()
    threading.Thread(target=_auto_login, args=(app,), daemon=True).start()

    return app


def _auto_login(app):
    """启动时自动登录（如果配置了账号密码）"""
    import time
    time.sleep(2)  # 等 CDN 域名先加载
    try:
        settings = load_settings(SETTINGS_FILE)
        username = settings.get('jm_username', '').strip()
        password = settings.get('jm_password', '').strip()
        if not username or not password:
            return

        from jmcomic import create_option_by_str
        from option_builder import build_option_yaml
        yaml_str = build_option_yaml(settings)
        option = create_option_by_str(yaml_str)
        client = option.new_jm_client()

        client.login(username, password)
        # 存到 app.config 供 favorites 路由使用
        app.config['jm_client'] = client
        # 通知 favorites 路由
        import routes.api_favorites as fav
        fav._auth_client = client
        fav._auth_username = username
        fav._last_login_time = time.time()
        print(f'[启动] 已自动登录: {username}')
    except Exception as e:
        print(f'[启动] 自动登录失败: {e}')


if __name__ == '__main__':
    print("=" * 50)
    print("  JMComic Downloader Web UI")
    print(f"  http://{SERVER_HOST}:{SERVER_PORT}")
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    app = create_app()
    app.run(
        host=SERVER_HOST,
        port=SERVER_PORT,
        debug=False,
        threaded=True
    )
