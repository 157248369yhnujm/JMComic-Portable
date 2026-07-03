"""搜索 API — 支持站点搜索、作者搜索、标签搜索等
高级搜索语法（JM API 原生支持）:
  全彩 +人妻      → 必须同时包含「全彩」和「人妻」(AND)
  全彩 -人妻      → 包含「全彩」但排除「人妻」(NOT)
  全彩 人妻       → 包含「全彩」或「人妻」(OR，默认行为)
"""

from flask import Blueprint, request, jsonify
from jmcomic import JmOption, JmModuleConfig

search_bp = Blueprint('search', __name__)


def get_client():
    """获取或创建 jmcomic 客户端（从 app.config 缓存）"""
    from flask import current_app
    client = current_app.config.get('jm_client')
    if client is None:
        from option_builder import load_settings
        from config import SETTINGS_FILE
        from option_builder import build_option
        settings = load_settings(SETTINGS_FILE)
        option = build_option(settings)
        client = option.new_jm_client()
        current_app.config['jm_client'] = client
    return client


def clear_client_cache():
    """清除客户端缓存（设置变更后调用）"""
    from flask import current_app
    current_app.config['jm_client'] = None


def serialize_page(page):
    """将 JmSearchPage 序列化为 JSON"""
    items = []
    if page is None:
        return {"items": [], "total": 0, "page_count": 0, "current_page": 1}

    for content_item in getattr(page, 'content', []):
        if isinstance(content_item, (list, tuple)) and len(content_item) >= 2:
            album_id, info = content_item[0], content_item[1]
            if isinstance(info, dict):
                items.append({
                    "album_id": str(album_id),
                    "name": info.get('name', ''),
                    "author": info.get('author', ''),
                    "tags": info.get('tags', []),
                    "views": info.get('views', ''),
                    "likes": info.get('likes', ''),
                    "page_count": info.get('pages', 0) or info.get('total_pages', 0)
                })

    return {
        "items": items,
        "total": getattr(page, 'total', 0),
        "page_count": getattr(page, 'page_count', 0) or 1,
        "current_page": getattr(page, 'page', 1) or 1
    }


@search_bp.route('/api/search', methods=['GET'])
def search():
    """搜索本子
    参数说明:
      q: 搜索关键词（JM API 原生支持 +词 / -词 语法）
      type: 搜索类型 (0=站点搜索, 1=作品, 2=作者, 3=标签, 4=角色)
      page: 页码 (默认1)
      order: 排序方式 (mr=最新, mv=最多观看, mp=最多图片, tf=最多喜欢)
      time: 时间范围 (t=今天, w=本周, m=本月, a=全部)
      category: 分类
      sub_category: 子分类
    """
    try:
        query = request.args.get('q', '')
        search_type = int(request.args.get('type', '0'))
        page_num = int(request.args.get('page', '1'))
        order_by = request.args.get('order', 'mr')
        time_range = request.args.get('time', 'a')
        category = request.args.get('category', None)
        sub_category = request.args.get('sub_category', None)

        if not query and search_type == 0:
            return jsonify({"success": False, "error": "请输入搜索关键词"})

        client = get_client()

        # 根据搜索类型调用不同的方法
        search_funcs = {
            0: client.search_site,
            1: client.search_work,
            2: client.search_author,
            3: client.search_tag,
            4: client.search_actor,
        }

        search_func = search_funcs.get(search_type, client.search_site)

        # 构建参数
        kwargs = {
            'page': page_num,
            'order_by': order_by,
            'time': time_range,
        }

        if search_type == 0:
            # 站点搜索支持分类
            if category:
                kwargs['category'] = category
            if sub_category:
                kwargs['sub_category'] = sub_category

        # 查询直接透传给 JM API（原生支持 +词 / -词 语法）
        page = search_func(query, **kwargs)

        data = serialize_page(page)
        data['current_page'] = page_num

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": f"搜索失败: {str(e)}"})
