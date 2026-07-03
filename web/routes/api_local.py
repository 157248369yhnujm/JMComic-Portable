"""本地漫画管理 API — 扫描下载目录、本地文件优先读取、ZIP 回退"""

import os
import io
import re
import time
import zipfile
import threading
from flask import Blueprint, request, jsonify, send_file, current_app

local_bp = Blueprint('local', __name__)

# ========== 专辑元数据缓存（减少 JM API 调用） ==========
# 结构: {album_id: {"title": str, "episodes": [{"photo_id":..., "sort":...}, ...], "ts": float}}
_album_meta_cache = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 3600  # 缓存1小时


def _get_download_dir():
    from option_builder import load_settings
    from config import SETTINGS_FILE
    settings = load_settings(SETTINGS_FILE)
    return settings.get('download_dir', '')


def _find_album_dir(album_title: str) -> str | None:
    """根据 album title 查找本地目录（精确 + 模糊匹配）"""
    download_dir = _get_download_dir()
    if not download_dir or not os.path.isdir(download_dir):
        return None

    candidate = os.path.join(download_dir, album_title)
    if os.path.isdir(candidate):
        return candidate

    try:
        for entry in os.listdir(download_dir):
            entry_path = os.path.join(download_dir, entry)
            if not os.path.isdir(entry_path) or entry == 'zip':
                continue
            if entry == album_title or album_title in entry or entry in album_title:
                return entry_path
    except OSError:
        pass

    return None


def _find_zip_for_album(album_id: str, album_title: str) -> str | None:
    """查找对应 album 的 ZIP 文件"""
    download_dir = _get_download_dir()
    if not download_dir:
        return None

    zip_dir = os.path.join(download_dir, 'zip')
    if not os.path.isdir(zip_dir):
        return None

    safe_title = album_title.replace('/', '_').replace('\\', '_').replace(':', '_') \
                            .replace('*', '_').replace('?', '_').replace('"', '_') \
                            .replace('<', '_').replace('>', '_').replace('|', '_')
    exact_path = os.path.join(zip_dir, f'[JM{album_id}] {safe_title}.zip')
    if os.path.isfile(exact_path):
        return exact_path

    prefix = f'[JM{album_id}]'
    try:
        for entry in os.listdir(zip_dir):
            if entry.startswith(prefix) and entry.endswith('.zip'):
                return os.path.join(zip_dir, entry)
    except OSError:
        pass

    return None


def _get_cached_album_meta(album_id: str) -> dict | None:
    """从缓存获取专辑元数据"""
    with _cache_lock:
        entry = _album_meta_cache.get(str(album_id))
        if entry and (time.time() - entry['ts']) < _CACHE_TTL:
            return entry
    return None


def _cache_album_meta(album_id: str, album_title: str, episodes: list):
    """缓存专辑元数据"""
    with _cache_lock:
        _album_meta_cache[str(album_id)] = {
            'title': album_title,
            'episodes': episodes,
            'ts': time.time(),
        }


def _fetch_album_meta(album_id: str):
    """获取并缓存专辑元数据（album_title + episode list with sort）"""
    cached = _get_cached_album_meta(album_id)
    if cached:
        return cached['title'], cached['episodes']

    from option_builder import load_settings, build_option
    from config import SETTINGS_FILE
    settings = load_settings(SETTINGS_FILE)
    option = build_option(settings)
    client = option.new_jm_client()
    album = client.get_album_detail(album_id)
    if not album:
        return '', []

    album_title = getattr(album, 'name', '') or getattr(album, 'title', '') or ''
    raw_episodes = getattr(album, 'episode_list', []) or []
    episodes = []
    for ep in raw_episodes:
        pid = ep[0] if isinstance(ep, (list, tuple)) else ep.get('photo_id', '')
        sort_val = ep[1] if isinstance(ep, (list, tuple)) and len(ep) > 1 else ep.get('sort', '0')
        episodes.append({
            'photo_id': str(pid) if pid else '',
            'sort': str(sort_val or '0').zfill(3),
        })

    _cache_album_meta(album_id, album_title, episodes)
    return album_title, episodes


def _list_local_albums():
    """扫描下载目录，返回所有本地已有的 album 信息"""
    download_dir = _get_download_dir()
    if not download_dir or not os.path.isdir(download_dir):
        return []

    albums = []
    try:
        entries = os.listdir(download_dir)
    except OSError:
        return []

    for entry in sorted(entries):
        entry_path = os.path.join(download_dir, entry)
        if not os.path.isdir(entry_path) or entry == 'zip':
            continue

        images = []
        total_size = 0
        chapter_prefixes = set()
        chapter_counts = {}  # 每章节图片数

        try:
            for f in os.listdir(entry_path):
                fpath = os.path.join(entry_path, f)
                if os.path.isfile(fpath):
                    ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                    if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
                        images.append(f)
                        total_size += os.path.getsize(fpath)
                        if '_' in f:
                            prefix = f.split('_')[0]
                            if prefix.isdigit() and len(prefix) == 3:
                                chapter_prefixes.add(prefix)
                                chapter_counts[prefix] = chapter_counts.get(prefix, 0) + 1
        except OSError:
            pass

        if not images:
            continue

        # 从目录名/文件名提取 album_id
        aid_match = re.search(r'JM(\d+)', entry)
        album_id = aid_match.group(1) if aid_match else None

        if not album_id:
            for img in images[:5]:
                aid_match2 = re.search(r'JM(\d+)', img)
                if aid_match2:
                    album_id = aid_match2.group(1)
                    break

        # 检查 ZIP
        has_zip = False
        if album_id:
            has_zip = _find_zip_for_album(album_id, entry) is not None

        # 目录修改时间（取目录mtime和最新文件mtime中的较大值）
        dir_mtime = os.path.getmtime(entry_path)
        file_mtimes = []
        try:
            for f in os.listdir(entry_path):
                fpath = os.path.join(entry_path, f)
                if os.path.isfile(fpath):
                    try:
                        file_mtimes.append(os.path.getmtime(fpath))
                    except OSError:
                        pass
        except OSError:
            pass
        latest_mtime = max([dir_mtime] + file_mtimes) if file_mtimes else dir_mtime

        albums.append({
            'album_title': entry,
            'album_id': album_id,
            'image_count': len(images),
            'chapter_count': len(chapter_prefixes) if chapter_prefixes else 1,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'chapter_prefixes': sorted(list(chapter_prefixes)),
            'chapter_counts': {k: chapter_counts.get(k, 0) for k in sorted(chapter_prefixes)},
            'has_zip': has_zip,
            'first_image': sorted(images)[0] if images else None,
            'mtime': latest_mtime,
        })

    # ZIP-only albums（跳过已有对应文件夹的）
    zip_dir = os.path.join(download_dir, 'zip')
    if os.path.isdir(zip_dir):
        # 先收集已有 album 的 title 和 id
        existing_titles = {a['album_title']: a for a in albums}
        existing_ids = {a['album_id'] for a in albums if a['album_id']}

        try:
            for entry in os.listdir(zip_dir):
                if not entry.endswith('.zip'):
                    continue
                aid_match = re.search(r'JM(\d+)', entry)
                aid = aid_match.group(1) if aid_match else None

                # 提取 ZIP 标题
                zip_title = re.sub(r'^\[JM\d+\]\s*', '', entry)
                zip_title = re.sub(r'\.zip$', '', zip_title)

                # 已存在对应文件夹？
                already = False
                if aid and aid in existing_ids:
                    already = True
                if not already:
                    # 模糊匹配已有文件夹标题
                    for etitle in existing_titles:
                        if zip_title == etitle or zip_title in etitle or etitle in zip_title:
                            already = True
                            # 补全已有条目的 album_id 和 has_zip
                            if aid and not existing_titles[etitle].get('album_id'):
                                existing_titles[etitle]['album_id'] = aid
                            existing_titles[etitle]['has_zip'] = True
                            break

                if already:
                    continue

                zip_path = os.path.join(zip_dir, entry)
                zip_size = os.path.getsize(zip_path)
                albums.append({
                    'album_title': zip_title,
                    'album_id': aid,
                    'image_count': 0,
                    'chapter_count': 0,
                    'total_size_bytes': zip_size,
                    'total_size_mb': round(zip_size / (1024 * 1024), 2),
                    'chapter_prefixes': [],
                    'has_zip': True,
                    'zip_only': True,
                    'first_image': None,
                    'mtime': os.path.getmtime(zip_path),
                })
        except OSError:
            pass

    return albums


# ==================== API 路由 ====================

@local_bp.route('/api/local/check/<album_id>', methods=['GET'])
def check_local_by_id(album_id):
    """纯本地预检：按 album_id 查 zip 文件名，判断是否已下载。

    全程零 JM API：仅靠 zip/ 下 [JM{id}].zip 前缀定位，
    再读 zip 内文件名按 XXX_ 前缀聚合章节列表。
    供前端"本地有则转本地阅读入口、零 API 阅读"使用。
    目录模式（无 zip）本地无 album_id 锚点，返回 has_local=false 回退在线。
    """
    try:
        album_id = str(album_id)
        # 传空 title → 精确路径必 miss，直接走前缀扫描 [JM{id}]
        zip_path = _find_zip_for_album(album_id, '')
        if not zip_path or not os.path.isfile(zip_path):
            return jsonify({"success": True, "data": {"has_local": False, "album_id": album_id}})

        # 读 zip 内文件名，按数字前缀聚合章节（与 list_zip_images 同款逻辑，纯本地）
        chapters = []
        with zipfile.ZipFile(zip_path, 'r') as zf:
            ch_set = set()
            for f in zf.namelist():
                if '_' in f:
                    prefix = f.split('_')[0]
                    if prefix.isdigit():
                        ch_set.add(prefix)
            chapters = sorted(ch_set)

        return jsonify({
            "success": True,
            "data": {
                "has_local": True,
                "mode": "zip",
                "album_id": album_id,
                "chapters": chapters if chapters else ['001'],
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/albums', methods=['GET'])
def get_local_albums():
    """获取所有本地漫画列表"""
    try:
        albums = _list_local_albums()
        return jsonify({"success": True, "data": {"albums": albums}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/album/<album_id>', methods=['GET'])
def get_local_album_info(album_id):
    """获取指定 album 的本地文件信息"""
    try:
        album_title, episodes = _fetch_album_meta(album_id)
        if not album_title:
            return jsonify({"success": False, "error": "本子不存在"}), 404

        album_dir = _find_album_dir(album_title)
        zip_path = _find_zip_for_album(album_id, album_title)

        chapter_info = []
        for ep in episodes:
            pid = ep['photo_id']
            if not pid:
                continue
            ep_sort = ep['sort']

            local_images = []
            if album_dir and os.path.isdir(album_dir):
                try:
                    for f in sorted(os.listdir(album_dir)):
                        if f.startswith(f'{ep_sort}_'):
                            fpath = os.path.join(album_dir, f)
                            if os.path.isfile(fpath):
                                ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                                if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
                                    local_images.append(f)
                except OSError:
                    pass

            chapter_info.append({
                'photo_id': pid,
                'sort': ep_sort,
                'local_image_count': len(local_images),
                'is_local': len(local_images) > 0,
            })

        total_local_images = sum(c['local_image_count'] for c in chapter_info)
        total_chapters_local = sum(1 for c in chapter_info if c['is_local'])

        return jsonify({"success": True, "data": {
            "album_id": str(album_id),
            "album_title": album_title,
            "album_dir": album_dir,
            "has_zip": zip_path is not None,
            "total_local_images": total_local_images,
            "total_local_chapters": total_chapters_local,
            "total_chapters": len(chapter_info),
            "chapters": chapter_info,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/photo/<album_id>/<photo_id>', methods=['GET'])
def check_local_photo(album_id, photo_id):
    """检查某章节的本地文件状态"""
    try:
        album_title, episodes = _fetch_album_meta(album_id)
        if not album_title:
            return jsonify({"success": False, "error": "本子不存在"}), 404

        album_dir = _find_album_dir(album_title)
        zip_path = _find_zip_for_album(album_id, album_title)

        ep_sort = '000'
        for ep in episodes:
            if ep['photo_id'] == str(photo_id):
                ep_sort = ep['sort']
                break

        local_images = []
        if album_dir and os.path.isdir(album_dir):
            try:
                for f in sorted(os.listdir(album_dir)):
                    if f.startswith(f'{ep_sort}_'):
                        fpath = os.path.join(album_dir, f)
                        if os.path.isfile(fpath):
                            ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                            if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
                                local_images.append(f)
            except OSError:
                pass

        return jsonify({"success": True, "data": {
            "album_id": str(album_id),
            "photo_id": str(photo_id),
            "ep_sort": ep_sort,
            "local_images": local_images,
            "has_local_files": len(local_images) > 0,
            "local_image_count": len(local_images),
            "has_zip": zip_path is not None,
            "album_dir": album_dir,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/image/<album_id>/<photo_id>/<int:page_index>', methods=['GET'])
def serve_local_image(album_id, photo_id, page_index):
    """
    本地优先图片服务：本地文件 → ZIP提取 → CDN在线
    使用元数据缓存避免重复 JM API 调用。
    """
    try:
        # ---- 尝试本地文件（用缓存的元数据） ----
        album_title, episodes = _fetch_album_meta(album_id)
        if album_title:
            # 找到该章节的 sort 索引
            ep_sort = '000'
            for ep in episodes:
                if ep['photo_id'] == str(photo_id):
                    ep_sort = ep['sort']
                    break

            # 还需要图片文件名 — 先查本地目录能不能不调API就匹配到
            album_dir = _find_album_dir(album_title)
            if album_dir and os.path.isdir(album_dir):
                # 扫描本地目录找到该章节的第一张图，获取图片命名规则
                try:
                    for f in sorted(os.listdir(album_dir)):
                        if f.startswith(f'{ep_sort}_'):
                            # 提取图片名（去掉前缀）: 001_00001.webp → 00001.webp
                            rest = f[len(ep_sort) + 1:]  # 跳过 "001_"
                            img_name = rest
                            if page_index == 0:
                                # 直接服务找到的第一张
                                fpath = os.path.join(album_dir, f)
                                ext = img_name.rsplit('.', 1)[-1].lower() if '.' in img_name else 'webp'
                                mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                            'png': 'image/png', 'webp': 'image/webp',
                                            'gif': 'image/gif', 'bmp': 'image/bmp'}
                                return send_file(fpath, mimetype=mime_map.get(ext, 'image/png'))

                            # 对于非首页，需要知道确切的图片名
                            # 从第一张图片推断命名模式
                            base_name = rest  # e.g. "00001.webp"
                            # 计算目标图片名: 00001 → 0000{page_index+1}
                            base_no_ext = base_name.rsplit('.', 1)[0]
                            ext = base_name.rsplit('.', 1)[-1]
                            # 保持相同位数
                            target_name = str(page_index + 1).zfill(len(base_no_ext))
                            target_file = f'{ep_sort}_{target_name}.{ext}'
                            target_path = os.path.join(album_dir, target_file)
                            if os.path.isfile(target_path):
                                mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                            'png': 'image/png', 'webp': 'image/webp',
                                            'gif': 'image/gif', 'bmp': 'image/bmp'}
                                return send_file(target_path, mimetype=mime_map.get(ext, 'image/png'))
                            break  # 只检查第一个匹配的，推断命名模式
                except OSError:
                    pass

            # 检查 ZIP
            zip_path = _find_zip_for_album(album_id, album_title)
            if zip_path and os.path.isfile(zip_path):
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        prefix = f'{ep_sort}_'
                        for name in sorted(zf.namelist()):
                            if name.startswith(prefix):
                                rest = name[len(prefix):]
                                if page_index == 0:
                                    data = zf.read(name)
                                    ext = rest.rsplit('.', 1)[-1].lower() if '.' in rest else 'webp'
                                    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                                'png': 'image/png', 'webp': 'image/webp',
                                                'gif': 'image/gif', 'bmp': 'image/bmp'}
                                    return send_file(io.BytesIO(data), mimetype=mime_map.get(ext, 'image/png'))

                                base_no_ext = rest.rsplit('.', 1)[0]
                                ext = rest.rsplit('.', 1)[-1]
                                target_name = str(page_index + 1).zfill(len(base_no_ext))
                                target_file = f'{ep_sort}_{target_name}.{ext}'
                                if target_file in zf.namelist():
                                    data = zf.read(target_file)
                                    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                                'png': 'image/png', 'webp': 'image/webp',
                                                'gif': 'image/gif', 'bmp': 'image/bmp'}
                                    return send_file(io.BytesIO(data), mimetype=mime_map.get(ext, 'image/png'))
                                break
                except Exception:
                    pass

        # ---- 回退：CDN 在线获取（需要 API 调用获取图片细节） ----
        from option_builder import load_settings, build_option
        from config import SETTINGS_FILE
        settings = load_settings(SETTINGS_FILE)
        option = build_option(settings)
        client = option.new_jm_client()

        photo = client.get_photo_detail(photo_id, fetch_album=False)
        if not photo:
            return jsonify({"success": False, "error": "章节不存在"}), 404

        page_arr = getattr(photo, 'page_arr', [])
        if not page_arr or page_index >= len(page_arr):
            return jsonify({"success": False, "error": "页码超出范围"}), 404

        img_name = page_arr[page_index]
        img_name_no_ext = img_name.rsplit('.', 1)[0] if '.' in img_name else img_name
        scramble_id = getattr(photo, 'scramble_id', '220980')
        cdn_domain = (getattr(photo, 'data_original_domain', None)
                      or current_app.config.get('cdn_domain')
                      or 'cdn-msp.jmapiproxy2.cc')
        query_params = getattr(photo, 'data_original_query_params', '') or ''

        img_url = f"https://{cdn_domain}/media/photos/{photo_id}/{img_name}{query_params}"

        from routes.api_cover import _download_image, _descramble_image
        img_data = _download_image(img_url)
        if not img_data:
            return jsonify({"success": False, "error": "下载图片失败"}), 500

        descrambled = _descramble_image(img_data, scramble_id, photo_id, img_name_no_ext)
        return send_file(io.BytesIO(descrambled), mimetype='image/png')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/cover/<album_id>', methods=['GET'])
def serve_local_cover(album_id):
    """优先返回本地封面图（ZIP→文件夹扫描），没有则回退到在线获取"""
    try:
        download_dir = _get_download_dir()
        if not download_dir:
            return jsonify({"success": False, "error": "下载目录不存在"}), 404

        # 第1步：检查 ZIP（最可靠，有 album_id 可精确匹配）
        zip_dir = os.path.join(download_dir, 'zip')
        if os.path.isdir(zip_dir):
            for entry in os.listdir(zip_dir):
                if entry.startswith(f'[JM{album_id}]') and entry.endswith('.zip'):
                    zip_path = os.path.join(zip_dir, entry)
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            for name in sorted(zf.namelist()):
                                if '_' in name:
                                    data = zf.read(name)
                                    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else 'webp'
                                    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                                'png': 'image/png', 'webp': 'image/webp'}
                                    return send_file(io.BytesIO(data), mimetype=mime_map.get(ext, 'image/png'))
                    except Exception:
                        pass
                    break  # 找到zip就停，不遍历更多

        # 第2步：尝试匹配文件夹（需要 title，从缓存或zip文件名获取）
        album_title = ''
        cached = _get_cached_album_meta(album_id)
        if cached:
            album_title = cached.get('title', '')
        if not album_title:
            # 从zip文件名推断title
            if os.path.isdir(zip_dir):
                for entry in os.listdir(zip_dir):
                    if entry.startswith(f'[JM{album_id}]'):
                        album_title = re.sub(r'^\[JM\d+\]\s*', '', entry)
                        album_title = re.sub(r'\.zip$', '', album_title)
                        break

        if album_title:
            album_dir = _find_album_dir(album_title)
            if album_dir and os.path.isdir(album_dir):
                for f in sorted(os.listdir(album_dir)):
                    fpath = os.path.join(album_dir, f)
                    if os.path.isfile(fpath):
                        ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                        if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
                            mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                        'png': 'image/png', 'webp': 'image/webp',
                                        'gif': 'image/gif', 'bmp': 'image/bmp'}
                            return send_file(fpath, mimetype=mime_map.get(ext, 'image/png'))

        # 第3步：在线回退（需要联网）
        try:
            from routes.api_cover import get_cover_image as _online_cover
            return _online_cover(album_id)
        except Exception:
            return jsonify({"success": False, "error": "无法获取封面（离线且无本地文件）"}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/dir-cover', methods=['GET'])
def serve_dir_cover():
    """
    根据下载目录名直接服务封面图（无需 album_id）。
    用第一个匹配的图片作为封面。
    ?name=<url_encoded_dir_name>
    """
    try:
        dir_name = request.args.get('name', '')
        if not dir_name:
            return jsonify({"success": False, "error": "缺少 name 参数"}), 400

        download_dir = _get_download_dir()
        if not download_dir:
            return jsonify({"success": False, "error": "下载目录不存在"}), 404

        # 安全：只允许 download_dir 下的子目录
        target_dir = os.path.normpath(os.path.join(download_dir, dir_name))
        if not target_dir.startswith(os.path.normpath(download_dir)):
            return jsonify({"success": False, "error": "非法路径"}), 403

        if not os.path.isdir(target_dir):
            return jsonify({"success": False, "error": "目录不存在"}), 404

        # 找第一个图片文件
        for f in sorted(os.listdir(target_dir)):
            fpath = os.path.join(target_dir, f)
            if os.path.isfile(fpath):
                ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
                    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                                'png': 'image/png', 'webp': 'image/webp',
                                'gif': 'image/gif', 'bmp': 'image/bmp'}
                    return send_file(fpath, mimetype=mime_map.get(ext, 'image/png'))

        return jsonify({"success": False, "error": "目录中没有图片"}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/dir-images', methods=['GET'])
def list_dir_images():
    """
    列出下载目录中某章节的所有图片文件名。
    ?name=<url_encoded_dir_name>&chapter=<chapter_prefix, e.g. 001>
    """
    try:
        dir_name = request.args.get('name', '')
        chapter = request.args.get('chapter', '001')

        if not dir_name:
            return jsonify({"success": False, "error": "缺少 name 参数"}), 400

        download_dir = _get_download_dir()
        if not download_dir:
            return jsonify({"success": False, "error": "下载目录不存在"}), 404

        target_dir = os.path.normpath(os.path.join(download_dir, dir_name))
        if not target_dir.startswith(os.path.normpath(download_dir)):
            return jsonify({"success": False, "error": "非法路径"}), 403

        if not os.path.isdir(target_dir):
            return jsonify({"success": False, "error": "目录不存在"}), 404

        images = []
        try:
            for f in sorted(os.listdir(target_dir)):
                if f.startswith(f'{chapter}_'):
                    fpath = os.path.join(target_dir, f)
                    if os.path.isfile(fpath):
                        ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                        if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
                            images.append(f)
        except OSError:
            pass

        return jsonify({"success": True, "data": {"images": images, "count": len(images)}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/dir-image', methods=['GET'])
def serve_dir_image():
    """
    直接服务下载目录中的图片文件。
    ?name=<url_encoded_dir_name>&file=<filename>
    """
    try:
        dir_name = request.args.get('name', '')
        filename = request.args.get('file', '')

        if not dir_name or not filename:
            return jsonify({"success": False, "error": "缺少参数"}), 400

        download_dir = _get_download_dir()
        if not download_dir:
            return jsonify({"success": False, "error": "下载目录不存在"}), 404

        target_dir = os.path.normpath(os.path.join(download_dir, dir_name))
        if not target_dir.startswith(os.path.normpath(download_dir)):
            return jsonify({"success": False, "error": "非法路径"}), 403

        file_path = os.path.join(target_dir, filename)
        if not os.path.normpath(file_path).startswith(target_dir):
            return jsonify({"success": False, "error": "非法路径"}), 403

        if not os.path.isfile(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404

        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'webp'
        mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'png': 'image/png', 'webp': 'image/webp',
                    'gif': 'image/gif', 'bmp': 'image/bmp'}
        return send_file(file_path, mimetype=mime_map.get(ext, 'image/png'))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/zip-images', methods=['GET'])
def list_zip_images():
    """
    列出 ZIP 压缩包内所有图片文件名（按章节前缀分组）。
    纯本地操作，无需 JM API。
    ?album_id=<id>
    """
    try:
        album_id = request.args.get('album_id', '')
        if not album_id:
            return jsonify({"success": False, "error": "缺少 album_id"}), 400

        # 直接从 ZIP 目录扫描（不依赖 JM API）
        download_dir = _get_download_dir()
        zip_dir = os.path.join(download_dir, 'zip') if download_dir else ''
        if not os.path.isdir(zip_dir):
            return jsonify({"success": False, "error": "ZIP 目录不存在"}), 404

        for entry in os.listdir(zip_dir):
            if entry.startswith(f'[JM{album_id}]') and entry.endswith('.zip'):
                zip_path = os.path.join(zip_dir, entry)
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    all_files = sorted(zf.namelist())
                    chapters = {}
                    for f in all_files:
                        if '_' in f:
                            prefix = f.split('_')[0]
                            if prefix.isdigit():
                                chapters.setdefault(prefix, []).append(f)
                title = re.sub(r'^\[JM\d+\]\s*', '', entry)
                title = re.sub(r'\.zip$', '', title)
                return jsonify({"success": True, "data": {
                    "album_title": title,
                    "chapters": {k: {"files": v, "count": len(v)} for k, v in chapters.items()},
                    "total_images": len(all_files),
                }})

        return jsonify({"success": False, "error": "ZIP 文件不存在"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@local_bp.route('/api/local/zip-image', methods=['GET'])
def serve_zip_image():
    """
    从 ZIP 压缩包中提取并服务单张图片（纯本地操作）。
    ?album_id=<id>&file=<filename_in_zip>
    """
    try:
        album_id = request.args.get('album_id', '')
        filename = request.args.get('file', '')
        if not album_id or not filename:
            return jsonify({"success": False, "error": "缺少参数"}), 400

        # 直接从 ZIP 目录扫描（不依赖 JM API）
        download_dir = _get_download_dir()
        zip_dir = os.path.join(download_dir, 'zip') if download_dir else ''
        zip_path = None
        if os.path.isdir(zip_dir):
            for entry in os.listdir(zip_dir):
                if entry.startswith(f'[JM{album_id}]') and entry.endswith('.zip'):
                    zip_path = os.path.join(zip_dir, entry)
                    break

        if not zip_path or not os.path.isfile(zip_path):
            return jsonify({"success": False, "error": "ZIP 不存在"}), 404

        with zipfile.ZipFile(zip_path, 'r') as zf:
            if filename not in zf.namelist():
                return jsonify({"success": False, "error": "文件不存在"}), 404
            data = zf.read(filename)

        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'webp'
        mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'png': 'image/png', 'webp': 'image/webp',
                    'gif': 'image/gif', 'bmp': 'image/bmp'}
        return send_file(io.BytesIO(data), mimetype=mime_map.get(ext, 'image/png'))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
