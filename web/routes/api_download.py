"""下载 API — 启动、状态查询、取消、历史管理"""

from flask import Blueprint, request, jsonify

download_bp = Blueprint('download', __name__)


def get_manager():
    from flask import current_app
    return current_app.config['download_manager']


@download_bp.route('/api/download/album/<jm_id>', methods=['POST'])
def start_album_download(jm_id):
    """启动本子下载"""
    try:
        body = request.get_json(silent=True) or {}
        extras = {
            'export_zip': body.get('export_zip', False),
            'export_pdf': body.get('export_pdf', False),
            'export_long_img': body.get('export_long_img', False),
        }
        manager = get_manager()
        task_id = manager.start_album_download(jm_id, extras)
        return jsonify({"success": True, "data": {"task_id": task_id}})
    except Exception as e:
        return jsonify({"success": False, "error": f"启动下载失败: {str(e)}"})


@download_bp.route('/api/download/photo/<jm_id>', methods=['POST'])
def start_photo_download(jm_id):
    """启动章节下载"""
    try:
        body = request.get_json(silent=True) or {}
        extras = {
            'export_zip': body.get('export_zip', False),
            'export_pdf': body.get('export_pdf', False),
            'export_long_img': body.get('export_long_img', False),
        }
        manager = get_manager()
        task_id = manager.start_photo_download(jm_id, extras)
        return jsonify({"success": True, "data": {"task_id": task_id}})
    except Exception as e:
        return jsonify({"success": False, "error": f"启动下载失败: {str(e)}"})


@download_bp.route('/api/download/batch', methods=['POST'])
def start_batch_download():
    """批量下载"""
    try:
        body = request.get_json(silent=True) or {}
        jm_ids = body.get('ids', [])
        dtype = body.get('type', 'album')
        extras = {
            'export_zip': body.get('export_zip', False),
            'export_pdf': body.get('export_pdf', False),
            'export_long_img': body.get('export_long_img', False),
        }

        if not jm_ids:
            return jsonify({"success": False, "error": "请提供要下载的ID列表"})

        manager = get_manager()
        task_ids = manager.start_batch_download(jm_ids, dtype, extras)
        return jsonify({"success": True, "data": {"task_ids": task_ids, "count": len(task_ids)}})
    except Exception as e:
        return jsonify({"success": False, "error": f"批量下载失败: {str(e)}"})


@download_bp.route('/api/download/status/<task_id>', methods=['GET'])
def get_download_status(task_id):
    """查询下载任务状态"""
    try:
        manager = get_manager()
        task = manager.get_task(task_id)
        if task is None:
            return jsonify({"success": False, "error": "任务不存在"})
        return jsonify({"success": True, "data": task.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@download_bp.route('/api/download/list', methods=['GET'])
def list_downloads():
    """列出所有下载任务"""
    try:
        manager = get_manager()
        tasks = manager.list_tasks()
        # 按开始时间倒序排列
        tasks_sorted = sorted(tasks, key=lambda t: t.start_time, reverse=True)
        return jsonify({
            "success": True,
            "data": {
                "tasks": [t.to_dict() for t in tasks_sorted],
                "active_count": sum(1 for t in tasks if t.status in ('pending', 'running'))
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@download_bp.route('/api/download/cancel/<task_id>', methods=['POST'])
def cancel_download(task_id):
    """取消下载任务"""
    try:
        manager = get_manager()
        success = manager.cancel_task(task_id)
        if success:
            return jsonify({"success": True, "data": {"message": "已发送取消信号"}})
        else:
            return jsonify({"success": False, "error": "任务不存在或已完成"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@download_bp.route('/api/download/history', methods=['DELETE'])
def clear_history():
    """清除下载历史"""
    try:
        manager = get_manager()
        count = manager.clear_history()
        return jsonify({"success": True, "data": {"cleared": count}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
