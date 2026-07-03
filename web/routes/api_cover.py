"""封面图 API — CDN 域名缓存 + 封面解扰代理"""

import os
import io
import tempfile
import hashlib
from flask import Blueprint, request, jsonify, send_file, current_app

cover_bp = Blueprint('cover', __name__)

# 解扰后的封面缓存目录
COVER_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cover_cache')


def _get_cdn_domain():
    return current_app.config.get('cdn_domain')


def _get_client():
    client = current_app.config.get('jm_client')
    if client is None:
        from jmcomic import create_option_by_str
        from option_builder import load_settings, build_option_yaml
        from config import SETTINGS_FILE
        settings = load_settings(SETTINGS_FILE)
        yaml_str = build_option_yaml(settings)
        option = create_option_by_str(yaml_str)
        client = option.new_jm_client()
        current_app.config['jm_client'] = client
    return client


@cover_bp.route('/api/cdn-domain', methods=['GET'])
def get_cdn_domain_api():
    domain = _get_cdn_domain()
    if domain:
        return jsonify({"success": True, "data": {"domain": domain}})
    return jsonify({"success": False, "error": "CDN 域名尚未就绪"})


@cover_bp.route('/api/cover/<album_id>', methods=['GET'])
def get_cover_url(album_id):
    """返回封面图 URL（不解扰，仅 URL）"""
    domain = _get_cdn_domain()
    if not domain:
        return jsonify({"success": False, "error": "CDN域名未就绪"})
    cover_url = f"https://{domain}/media/photos/{album_id}/00001.webp"
    return jsonify({"success": True, "data": {"cover_url": cover_url, "album_id": str(album_id)}})


@cover_bp.route('/api/cover-img/<album_id>', methods=['GET'])
def get_cover_image(album_id):
    """
    获取解扰后的封面图片。
    下载 JM CDN 上的第一张图 → 用 scramble_id 解扰 → 返回 PNG
    结果会被缓存到 cover_cache 目录
    """
    try:
        # 检查缓存
        os.makedirs(COVER_CACHE_DIR, exist_ok=True)
        cache_key = hashlib.md5(f"cover_{album_id}".encode()).hexdigest()
        cache_path = os.path.join(COVER_CACHE_DIR, f"{cache_key}.png")

        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
            return send_file(cache_path, mimetype='image/png')

        # 获取本子详情以拿到 scramble_id
        client = _get_client()
        album = client.get_album_detail(album_id)
        if not album:
            return jsonify({"success": False, "error": "本子不存在"}), 404

        # 从第一个章节获取 scramble_id 和 CDN 域名
        scramble_id = None
        cdn_domain = _get_cdn_domain()
        first_img_url = None

        if hasattr(album, 'episode_list') and album.episode_list:
            first_ep = album.episode_list[0]
            photo_id = first_ep[0] if isinstance(first_ep, (list, tuple)) else first_ep.get('photo_id', '')
            if photo_id:
                photo = client.get_photo_detail(photo_id, fetch_album=False)
                if photo:
                    scramble_id = getattr(photo, 'scramble_id', None)
                    domain = getattr(photo, 'data_original_domain', None)
                    if domain:
                        cdn_domain = domain
                        current_app.config['cdn_domain'] = domain
                    if hasattr(photo, 'page_arr') and photo.page_arr:
                        first_img = photo.page_arr[0]
                        first_img_url = f"https://{cdn_domain}/media/photos/{photo_id}/{first_img}"
                        # 完整 URL 需要 query params
                        qp = getattr(photo, 'data_original_query_params', None)
                        if qp:
                            first_img_url += qp

        if not scramble_id:
            scramble_id = '220980'  # 默认 scramble_id
        if not first_img_url:
            first_img_url = f"https://{cdn_domain or 'cdn-msp.jmapiproxy2.cc'}/media/photos/{album_id}/00001.webp"

        # 下载并解扰
        from jmcomic import JmImageTool
        img_data = _download_image(first_img_url)
        if not img_data:
            return jsonify({"success": False, "error": "下载封面失败"}), 500

        descrambled = _descramble_image(img_data, scramble_id, album_id)

        # 保存缓存
        with open(cache_path, 'wb') as f:
            f.write(descrambled)

        return send_file(io.BytesIO(descrambled), mimetype='image/png')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


def _download_image(url: str) -> bytes:
    """通过 jmcomic client 下载图片"""
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/*,*/*;q=0.8',
            'Referer': 'https://18comic.vip/',
        }
        from config import SETTINGS_FILE
        from option_builder import load_settings
        settings = load_settings(SETTINGS_FILE)
        proxy = settings.get('proxy', '')
        proxies = {'http': proxy, 'https': proxy} if proxy and proxy not in ('null', 'None', '') else None
        resp = requests.get(url, headers=headers, timeout=15, proxies=proxies)
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception:
        return None


def _descramble_image(img_data: bytes, scramble_id: str, entity_id: str, img_name: str = '00001') -> bytes:
    """用 jmcomic 的 JmImageTool 解扰图片并返回 PNG 字节
    img_name: 图片文件名（如 00001.webp），不同图片需要不同的 scramble num
    """
    from jmcomic import JmImageTool
    from PIL import Image

    # 从字节加载 PIL Image
    img = Image.open(io.BytesIO(img_data))

    # 计算分割数 — 必须使用正确的图片文件名
    num = JmImageTool.get_num(str(scramble_id), str(entity_id), img_name)

    # 保存到临时文件
    tmp_out = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    tmp_out_path = tmp_out.name
    tmp_out.close()

    try:
        JmImageTool.decode_and_save(num, img, tmp_out_path)
        with open(tmp_out_path, 'rb') as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_out_path)
        except Exception:
            pass


@cover_bp.route('/api/batch-covers', methods=['POST'])
def batch_cover_urls():
    """批量获取封面 URL（不解扰，快速）"""
    domain = _get_cdn_domain()
    if not domain:
        return jsonify({"success": False, "error": "CDN域名未就绪"})

    body = request.get_json(silent=True) or {}
    album_ids = body.get('ids', [])
    covers = {}
    for aid in album_ids[:100]:
        # 用解扰代理地址 /api/cover-img/<id> 而不是原始 CDN URL
        covers[str(aid)] = f"/api/cover-img/{aid}"
    return jsonify({"success": True, "data": {"covers": covers}})


@cover_bp.route('/api/view-image/<photo_id>/<int:page_index>', methods=['GET'])
def get_view_image(photo_id, page_index):
    """
    在线观看用：获取解扰后的单页图片。
    优化：优先从本地文件/ZIP读取，没有再回退到 CDN 下载+解扰。
    """
    try:
        client = _get_client()
        photo = client.get_photo_detail(photo_id, fetch_album=True)
        if not photo:
            return jsonify({"success": False, "error": "章节不存在"}), 404

        page_arr = getattr(photo, 'page_arr', [])
        if not page_arr or page_index >= len(page_arr):
            return jsonify({"success": False, "error": "页码超出范围"}), 404

        img_name = page_arr[page_index]
        img_name_no_ext = img_name.rsplit('.', 1)[0] if '.' in img_name else img_name

        # ---- 尝试本地文件优先 ----
        album = getattr(photo, 'from_album', None)
        if album is not None:
            local_result = _try_serve_local_image(album, photo, photo_id, img_name, page_index)
            if local_result is not None:
                return local_result

        # ---- 回退：CDN 下载 + 解扰 ----
        scramble_id = getattr(photo, 'scramble_id', '220980')
        cdn_domain = getattr(photo, 'data_original_domain', None) or _get_cdn_domain() or 'cdn-msp.jmapiproxy2.cc'
        query_params = getattr(photo, 'data_original_query_params', '') or ''

        img_url = f"https://{cdn_domain}/media/photos/{photo_id}/{img_name}{query_params}"

        img_data = _download_image(img_url)
        if not img_data:
            return jsonify({"success": False, "error": "下载图片失败"}), 500

        descrambled = _descramble_image(img_data, scramble_id, photo_id, img_name_no_ext)
        return send_file(io.BytesIO(descrambled), mimetype='image/png')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


def _try_serve_local_image(album, photo, photo_id, img_name, page_index):
    """
    尝试从本地文件或 ZIP 提供图片。
    成功返回 Flask response，失败返回 None（回退到 CDN）。
    优化：优先直接扫描本地目录，避免额外API调用。
    """
    import os as _os
    import io as _io
    import zipfile as _zf

    album_title = getattr(album, 'name', '') or getattr(album, 'title', '') or ''
    album_id = str(getattr(album, 'album_id', ''))

    from option_builder import load_settings
    from config import SETTINGS_FILE
    settings = load_settings(SETTINGS_FILE)
    download_dir = settings.get('download_dir', '')

    if not download_dir or not _os.path.isdir(download_dir):
        return None

    # 获取章节 sort 索引
    ep_sort = '000'
    episodes = getattr(album, 'episode_list', []) or []
    for ep in episodes:
        pid = ep[0] if isinstance(ep, (list, tuple)) else ep.get('photo_id', '')
        if str(pid) == str(photo_id):
            ep_sort = str(ep[1] if isinstance(ep, (list, tuple)) and len(ep) > 1
                          else ep.get('sort', '0') or '0').zfill(3)
            break

    # 找到本地目录
    album_dir = None
    candidate = _os.path.join(download_dir, album_title)
    if _os.path.isdir(candidate):
        album_dir = candidate
    else:
        try:
            for entry in _os.listdir(download_dir):
                entry_path = _os.path.join(download_dir, entry)
                if not _os.path.isdir(entry_path) or entry == 'zip':
                    continue
                if entry == album_title or album_title in entry or entry in album_title:
                    album_dir = entry_path
                    break
        except OSError:
            pass

    ext = img_name.rsplit('.', 1)[-1].lower() if '.' in img_name else 'webp'
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'webp': 'image/webp',
                'gif': 'image/gif', 'bmp': 'image/bmp'}

    # 第1步：检查本地图片文件（直接匹配）
    if album_dir:
        local_filename = f'{ep_sort}_{img_name}'
        local_path = _os.path.join(album_dir, local_filename)
        if _os.path.isfile(local_path):
            return send_file(local_path, mimetype=mime_map.get(ext, 'image/png'))

    # 第2步：检查 ZIP 压缩包
    zip_dir = _os.path.join(download_dir, 'zip')
    if _os.path.isdir(zip_dir):
        zip_path = None
        safe_title = album_title.replace('/', '_').replace('\\', '_').replace(':', '_') \
                                .replace('*', '_').replace('?', '_').replace('"', '_') \
                                .replace('<', '_').replace('>', '_').replace('|', '_')
        exact_path = _os.path.join(zip_dir, f'[JM{album_id}] {safe_title}.zip')
        if _os.path.isfile(exact_path):
            zip_path = exact_path
        else:
            prefix = f'[JM{album_id}]'
            try:
                for entry in _os.listdir(zip_dir):
                    if entry.startswith(prefix) and entry.endswith('.zip'):
                        zip_path = _os.path.join(zip_dir, entry)
                        break
            except OSError:
                pass

        if zip_path and _os.path.isfile(zip_path):
            try:
                with _zf.ZipFile(zip_path, 'r') as zf:
                    zip_filename = f'{ep_sort}_{img_name}'
                    if zip_filename in zf.namelist():
                        data = zf.read(zip_filename)
                        return send_file(_io.BytesIO(data),
                                         mimetype=mime_map.get(ext, 'image/png'))
            except Exception:
                pass

    return None
