"""本子/章节详情 API"""

from flask import Blueprint, request, jsonify

album_bp = Blueprint('album', __name__)


def get_client():
    from flask import current_app
    client = current_app.config.get('jm_client')
    if client is None:
        from option_builder import load_settings, build_option
        from config import SETTINGS_FILE
        settings = load_settings(SETTINGS_FILE)
        option = build_option(settings)
        client = option.new_jm_client()
        current_app.config['jm_client'] = client
    return client


@album_bp.route('/api/album/<jm_id>', methods=['GET'])
def get_album(jm_id):
    """获取本子详情"""
    try:
        client = get_client()
        album = client.get_album_detail(jm_id)

        if album is None:
            return jsonify({"success": False, "error": f"本子 JM{jm_id} 不存在"})

        # 构建章节列表
        episode_list = []
        if hasattr(album, 'episode_list') and album.episode_list:
            for ep in album.episode_list:
                if isinstance(ep, (list, tuple)) and len(ep) >= 3:
                    episode_list.append({
                        "photo_id": str(ep[0]),
                        "index": str(ep[1]) if ep[1] else '',
                        "title": str(ep[2]) if ep[2] else ''
                    })
                elif isinstance(ep, dict):
                    episode_list.append({
                        "photo_id": str(ep.get('photo_id', '')),
                        "index": str(ep.get('index', '')),
                        "title": str(ep.get('title', ''))
                    })

        # 安全获取属性
        def safe_attr(obj, attr, default=''):
            val = getattr(obj, attr, default)
            if val is None:
                return default
            return val

        album_data = {
            "album_id": str(jm_id),
            "name": safe_attr(album, 'name') or safe_attr(album, 'title'),
            "description": safe_attr(album, 'description'),
            "authors": list(safe_attr(album, 'authors', [])) if hasattr(album, 'authors') and album.authors else [],
            "tags": list(safe_attr(album, 'tags', [])) if hasattr(album, 'tags') and album.tags else [],
            "works": list(safe_attr(album, 'works', [])) if hasattr(album, 'works') and album.works else [],
            "actors": list(safe_attr(album, 'actors', [])) if hasattr(album, 'actors') and album.actors else [],
            "views": safe_attr(album, 'views'),
            "likes": safe_attr(album, 'likes'),
            "comment_count": safe_attr(album, 'comment_count', 0),
            "page_count": safe_attr(album, 'page_count', 0),
            "pub_date": safe_attr(album, 'pub_date'),
            "update_date": safe_attr(album, 'update_date'),
            "episode_list": episode_list,
            "episode_count": len(episode_list) if episode_list else (len(album) if hasattr(album, '__len__') else 0),
        }

        return jsonify({"success": True, "data": album_data})
    except Exception as e:
        return jsonify({"success": False, "error": f"获取本子详情失败: {str(e)}"})


@album_bp.route('/api/photo/<jm_id>', methods=['GET'])
def get_photo(jm_id):
    """获取章节详情"""
    try:
        client = get_client()
        photo = client.get_photo_detail(jm_id)

        if photo is None:
            return jsonify({"success": False, "error": f"章节 JM{jm_id} 不存在"})

        def safe_attr(obj, attr, default=''):
            val = getattr(obj, attr, default)
            if val is None:
                return default
            return val

        photo_data = {
            "photo_id": str(jm_id),
            "name": safe_attr(photo, 'name') or safe_attr(photo, 'title'),
            "album_id": str(safe_attr(photo, 'album_id', jm_id)),
            "album_name": safe_attr(photo, 'from_album', None),
            "sort": safe_attr(photo, 'sort', 0),
            "image_count": len(photo) if hasattr(photo, '__len__') else 0,
            "page_arr": list(safe_attr(photo, 'page_arr', [])) if hasattr(photo, 'page_arr') and photo.page_arr else [],
        }

        if hasattr(photo, 'from_album') and photo.from_album:
            album = getattr(photo, 'from_album', None)
            if album:
                photo_data['album_name'] = safe_attr(album, 'name') or safe_attr(album, 'title', '')

        return jsonify({"success": True, "data": photo_data})
    except Exception as e:
        return jsonify({"success": False, "error": f"获取章节详情失败: {str(e)}"})
