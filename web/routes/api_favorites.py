"""收藏夹 API — 登录、查看收藏、添加收藏（支持 Token 过期自动刷新重试）"""

from flask import Blueprint, request, jsonify, current_app
import traceback
import threading
import time
import logging

favorites_bp = Blueprint('favorites', __name__)

# 已认证的客户端缓存
_auth_client = None
_auth_username = None
_last_login_time = 0
_login_lock = threading.Lock()

# Token 有效期约 4 小时，提前 30 分钟刷新
TOKEN_TTL = 4 * 3600
TOKEN_REFRESH_BEFORE = 1800  # 过期前30分钟


def _get_stored_credentials():
    """从设置中读取账号密码"""
    from option_builder import load_settings
    from config import SETTINGS_FILE
    settings = load_settings(SETTINGS_FILE)
    u = settings.get('jm_username', '').strip()
    p = settings.get('jm_password', '').strip()
    return (u, p) if u and p else (None, None)


def _do_login(client, username, password):
    """执行登录，成功返回 True"""
    try:
        client.login(username, password)
        return True
    except Exception:
        return False


def get_auth_client():
    """获取已认证客户端，过期自动刷新"""
    global _auth_client, _auth_username, _last_login_time

    with _login_lock:
        now = time.time()
        # 检查是否需要刷新
        if _auth_client and _auth_username and (now - _last_login_time) > (TOKEN_TTL - TOKEN_REFRESH_BEFORE):
            logging.getLogger('jmcomic').info('[Auth] Token 即将过期，自动刷新...')
            u, p = _get_stored_credentials()
            if u and p:
                new_client = _create_api_client()
                if _do_login(new_client, u, p):
                    _auth_client = new_client
                    _last_login_time = now
                    current_app.config['jm_client'] = new_client
                    logging.getLogger('jmcomic').info(f'[Auth] Token 刷新成功: {_auth_username}')

    return _auth_client, _auth_username


def _create_api_client():
    """创建一个用于 API 操作的客户端"""
    from jmcomic import create_option_by_str
    from option_builder import load_settings, build_option_yaml
    from config import SETTINGS_FILE

    settings = load_settings(SETTINGS_FILE)
    yaml_str = build_option_yaml(settings)
    option = create_option_by_str(yaml_str)
    return option.new_jm_client()


def get_client():
    """获取普通客户端（缓存）"""
    client = current_app.config.get('jm_client')
    if client is None:
        client = _create_api_client()
        current_app.config['jm_client'] = client
    return client


def serialize_favorites_page(page):
    items = []
    if page is None:
        return {"items": [], "total": 0, "page_count": 0, "current_page": 1, "folder_list": []}

    for content_item in getattr(page, 'content', []):
        if isinstance(content_item, (list, tuple)) and len(content_item) >= 2:
            album_id, info = content_item[0], content_item[1]
            if isinstance(info, dict):
                items.append({
                    "album_id": str(album_id),
                    "name": info.get('name', ''),
                    "author": info.get('author', ''),
                    "tags": info.get('tags', []),
                    "create_at": info.get('create_at', ''),
                })

    folder_list = []
    if hasattr(page, 'folder_list') and page.folder_list:
        for f in page.folder_list:
            if isinstance(f, dict):
                folder_list.append({
                    "folder_id": str(f.get('FID', '')),
                    "name": f.get('name', ''),
                })

    return {
        "items": items,
        "total": getattr(page, 'total', 0),
        "page_count": getattr(page, 'page_count', 0) or 1,
        "current_page": getattr(page, 'page', 1) or 1,
        "folder_list": folder_list,
    }


@favorites_bp.route('/api/login', methods=['POST'])
def login():
    """登录禁漫"""
    global _auth_client, _auth_username

    try:
        body = request.get_json(silent=True) or {}
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()

        if not username or not password:
            return jsonify({"success": False, "error": "请输入用户名和密码"})

        # 创建全新客户端用于登录（不共享缓存，确保域名新鲜）
        client = _create_api_client()

        # 先做一次轻量请求确保域名已更新
        try:
            client.get_domain_list()
        except Exception:
            pass

        # 执行登录
        resp = client.login(username, password)

        global _last_login_time
        _auth_client = client
        _auth_username = username
        _last_login_time = time.time()

        # 同时更新全局缓存客户端
        current_app.config['jm_client'] = client

        return jsonify({
            "success": True,
            "data": {
                "username": username,
                "message": "登录成功"
            }
        })

    except Exception as e:
        _auth_client = None
        _auth_username = None
        error_msg = str(e)
        # 提取有用的错误信息
        if hasattr(e, 'resp') and hasattr(e.resp, 'text'):
            error_msg += f" | 响应: {e.resp.text[:200]}"
        traceback.print_exc()
        return jsonify({"success": False, "error": f"登录失败: {error_msg}"})


@favorites_bp.route('/api/login/status', methods=['GET'])
def login_status():
    global _auth_username
    if _auth_username:
        return jsonify({"success": True, "data": {"logged_in": True, "username": _auth_username}})
    return jsonify({"success": True, "data": {"logged_in": False, "username": None}})


@favorites_bp.route('/api/logout', methods=['POST'])
def logout():
    global _auth_client, _auth_username, _last_login_time
    _auth_client = None
    _auth_username = None
    _last_login_time = 0
    return jsonify({"success": True, "data": {"message": "已退出登录"}})


@favorites_bp.route('/api/favorites', methods=['GET'])
def get_favorites():
    try:
        client, username = get_auth_client()
        if client is None:
            return jsonify({"success": False, "error": "请先登录"})

        page_num = int(request.args.get('page', '1'))
        order_by = request.args.get('order_by', 'mr')
        folder_id = request.args.get('folder_id', '0')

        try:
            page = client.favorite_folder(page=page_num, order_by=order_by, folder_id=folder_id)
        except Exception as e:
            err_msg = str(e)
            # 401 未授权 → 尝试重登录后重试
            if '401' in err_msg or '登入' in err_msg or 'login' in err_msg.lower():
                logging.getLogger('jmcomic').info('[Auth] 收到401，尝试重登录...')
                u, p = _get_stored_credentials()
                if u and p:
                    global _auth_client, _last_login_time
                    new_client = _create_api_client()
                    if _do_login(new_client, u, p):
                        _auth_client = new_client
                        _last_login_time = time.time()
                        current_app.config['jm_client'] = new_client
                        page = new_client.favorite_folder(page=page_num, order_by=order_by, folder_id=folder_id)
                    else:
                        raise Exception('重新登录失败，请检查账号密码')
                else:
                    raise Exception('Token已过期且未保存账号密码，请重新登录')
            else:
                raise

        data = serialize_favorites_page(page)
        return jsonify({"success": True, "data": data})

    except Exception as e:
        return jsonify({"success": False, "error": f"获取收藏夹失败: {str(e)}"})


@favorites_bp.route('/api/favorites/add/<album_id>', methods=['POST'])
def add_favorite(album_id):
    try:
        client, _ = get_auth_client()
        if client is None:
            return jsonify({"success": False, "error": "请先登录"})

        body = request.get_json(silent=True) or {}
        folder_id = body.get('folder_id', '0')

        client.add_favorite_album(album_id, folder_id=folder_id)
        return jsonify({"success": True, "data": {"message": "已添加到收藏夹", "album_id": album_id}})

    except Exception as e:
        return jsonify({"success": False, "error": f"添加收藏失败: {str(e)}"})
