"""排行榜/分类 API"""

from flask import Blueprint, request, jsonify
import types

ranking_bp = Blueprint('ranking', __name__)


def _patch_categories_filter(client):
    """修复 JM API categories_filter 的域名兼容性问题：
    部分域名对 mv_t(日排)/mv_w(周排) 返回空数据，但其他域名正常。
    遍历所有域名找到有数据的那个。
    注意：周排周一为空是正常行为，不要回退到总榜。
    """
    if getattr(client, '_categories_filter_patched', False):
        return

    def patched_categories_filter(self, page, time, category, order_by, sub_category=None):
        from jmcomic import JmPageTool
        from jmcomic.jm_config import JmMagicConstants

        o_val = f'{order_by}_{time}' if time != JmMagicConstants.TIME_ALL else order_by

        params = {
            'page': page,
            'order': '',
            'c': category,
            'o': o_val,
        }

        # 第一次请求（使用默认域名）
        resp = self.req_api(self.append_params_to_url(self.API_CATEGORIES_FILTER, params))
        result = JmPageTool.parse_api_to_search_page(resp.model_data)

        # 如果结果为空且用了时间过滤，尝试其他域名
        if len(getattr(result, 'content', [])) == 0 and time != JmMagicConstants.TIME_ALL:
            domain_list = self.get_domain_list()
            for domain in domain_list:
                try:
                    alt_url = f'https://{domain}{self.API_CATEGORIES_FILTER}'
                    alt_url = self.append_params_to_url(alt_url, params)
                    alt_resp = self.req_api(alt_url)
                    alt_result = JmPageTool.parse_api_to_search_page(alt_resp.model_data)
                    if len(getattr(alt_result, 'content', [])) > 0:
                        return alt_result
                except Exception:
                    continue
            # 所有域名都为空 — 可能是周一没周排之类的正常情况，返回原始空结果

        return result

    client.categories_filter = types.MethodType(patched_categories_filter, client)
    client._categories_filter_patched = True


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

    _patch_categories_filter(client)
    return client


def serialize_page(page):
    """将分页结果序列化"""
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


# 排行榜类型 → (time, order_by) 映射
# time: t=今日, w=本周, m=本月, a=全部
# order_by: mr=最新, mv=最多观看(总排行), tf=最多爱心, mp=最多图片
RANKING_CONFIG = {
    'daily':      ('t', 'mv', '日排行'),
    'weekly':     ('w', 'mv', '周排行'),
    'monthly':    ('m', 'mv', '月排行'),
    'latest':     ('a', 'mr', '最新'),
    'most_liked': ('a', 'tf', '最多爱心'),
    'all_time':   ('a', 'mv', '总排行'),
}


@ranking_bp.route('/api/ranking/<rank_type>', methods=['GET'])
def get_ranking(rank_type):
    """获取排行榜
    支持类型: daily, weekly, monthly, latest, most_liked, all_time
    """
    try:
        page_num = int(request.args.get('page', '1'))
        category = request.args.get('category', '0')

        config = RANKING_CONFIG.get(rank_type)
        if config is None:
            return jsonify({"success": False, "error": f"不支持的排行榜类型: {rank_type}"})

        time_val, order_by, label = config

        client = get_client()
        page = client.categories_filter(
            page=page_num,
            time=time_val,
            category=category,
            order_by=order_by,
        )
        data = serialize_page(page)
        data['current_page'] = page_num
        data['rank_type'] = rank_type

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": f"获取排行榜失败: {str(e)}"})


@ranking_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """分类浏览"""
    try:
        page_num = int(request.args.get('page', '1'))
        time_range = request.args.get('time', 'a')
        category = request.args.get('category', '0')
        order_by = request.args.get('order', 'mv')
        sub_category = request.args.get('sub_category', None)

        client = get_client()

        kwargs = {
            'page': page_num,
            'time': time_range,
            'category': category,
            'order_by': order_by,
        }
        if sub_category:
            kwargs['sub_category'] = sub_category

        page = client.categories_filter(**kwargs)
        data = serialize_page(page)
        data['current_page'] = page_num

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": f"获取分类失败: {str(e)}"})
