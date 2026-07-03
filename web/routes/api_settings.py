"""设置 API — 读取和保存用户设置"""

import os
import json
from flask import Blueprint, request, jsonify

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """获取当前用户设置"""
    try:
        from option_builder import load_settings
        from config import SETTINGS_FILE
        settings = load_settings(SETTINGS_FILE)
        return jsonify({"success": True, "data": settings})
    except Exception as e:
        return jsonify({"success": False, "error": f"获取设置失败: {str(e)}"})


@settings_bp.route('/api/settings', methods=['PUT'])
def update_settings():
    """更新用户设置"""
    try:
        from option_builder import save_settings, load_settings
        from config import SETTINGS_FILE

        body = request.get_json(silent=True) or {}
        if not body:
            return jsonify({"success": False, "error": "请提供要更新的设置"})

        current = load_settings(SETTINGS_FILE)
        current.update(body)
        save_settings(SETTINGS_FILE, current)

        # 清除缓存的客户端，使新设置生效
        from flask import current_app
        current_app.config['jm_client'] = None
        current_app.config['jm_option'] = None

        # 重置域名更新缓存，使新代理设置能触发域名重新拉取
        from jmcomic.jm_config import JmModuleConfig
        JmModuleConfig.DOMAIN_API_UPDATED_LIST = None
        # 重置固定时间戳缓存，使新设置(如代理)能用当前时间生成 token
        try:
            delattr(JmModuleConfig, '__cache_get_fix_ts_token_tokenparam__')
        except AttributeError:
            pass

        # 让 routes 模块也能清除缓存
        from routes.api_search import clear_client_cache
        clear_client_cache()

        return jsonify({"success": True, "data": current, "message": "设置已保存"})
    except Exception as e:
        return jsonify({"success": False, "error": f"保存设置失败: {str(e)}"})


@settings_bp.route('/api/settings/test-proxy', methods=['POST'])
def test_proxy():
    """测试代理连通性"""
    try:
        body = request.get_json(silent=True) or {}
        proxy = body.get('proxy', 'http://127.0.0.1:7890')

        import requests as req
        try:
            proxies = {"http": proxy, "https": proxy} if proxy else None
            resp = req.get("https://www.google.com", timeout=5, proxies=proxies)
            google_ok = resp.status_code == 200
        except Exception:
            google_ok = False

        try:
            resp = req.get("https://18comic.vip", timeout=5, proxies=proxies)
            jm_ok = resp.status_code == 200
        except Exception:
            jm_ok = False

        return jsonify({
            "success": True,
            "data": {
                "proxy": proxy,
                "google_accessible": google_ok,
                "jm_accessible": jm_ok,
                "message": "代理可用" if (google_ok or jm_ok) else "代理无法连通"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"测试失败: {str(e)}"})
