"""后台下载任务管理器 — 通过自定义 JmDownloader 子类追踪进度"""

import uuid
import threading
import time
import os
import traceback
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DownloadProgress:
    """下载进度信息"""
    current_photo: int = 0
    total_photos: int = 0
    current_image: int = 0
    total_images: int = 0
    current_photo_name: str = ''
    album_title: str = ''
    percentage: float = 0.0
    downloaded_mb: float = 0.0   # 已下载 MB
    total_mb: float = 0.0        # 预估总 MB
    download_speed: str = ''     # 下载速度


@dataclass
class DownloadTask:
    """单个下载任务"""
    task_id: str
    type: str          # 'album' 或 'photo'
    jm_id: str
    status: str = 'pending'
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    save_path: str = ''
    error: str = ''
    start_time: float = 0.0
    end_time: float = 0.0
    extras: dict = field(default_factory=dict)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _thread: Optional[threading.Thread] = None
    # 速度计算用
    _last_bytes: int = 0
    _last_time: float = 0.0

    def to_dict(self) -> dict:
        elapsed = 0
        if self.start_time > 0:
            if self.end_time > 0:
                elapsed = round(self.end_time - self.start_time, 1)
            else:
                elapsed = round(time.time() - self.start_time, 1)

        return {
            "task_id": self.task_id,
            "type": self.type,
            "jm_id": self.jm_id,
            "status": self.status,
            "progress": {
                "current_photo": self.progress.current_photo,
                "total_photos": self.progress.total_photos,
                "current_image": self.progress.current_image,
                "total_images": self.progress.total_images,
                "current_photo_name": self.progress.current_photo_name,
                "album_title": self.progress.album_title,
                "percentage": round(self.progress.percentage, 1),
                "downloaded_mb": round(self.progress.downloaded_mb, 2),
                "total_mb": round(self.progress.total_mb, 2),
                "download_speed": self.progress.download_speed,
            },
            "save_path": self.save_path,
            "error": self.error,
            "elapsed": elapsed,
            "extras": self.extras
        }


class DownloadCancelledException(Exception):
    pass


class ProgressDownloaderMixin:
    """
    混入 JmDownloader — 重写生命周期回调来追踪进度。
    实际类由 _make_progress_downloader 动态创建。
    """
    pass


def _make_progress_downloader(task: DownloadTask):
    """
    动态创建一个 JmDownloader 子类，注入进度追踪逻辑。
    因为我们需要闭包访问 task 对象，而 download_album 的 downloader 参数是类不是实例。
    """
    from jmcomic import JmDownloader

    class ProgressDownloader(JmDownloader):
        """自定义下载器：追踪进度到 DownloadTask"""

        def before_album(self, album):
            task.progress.album_title = (getattr(album, 'name', '') or
                                         getattr(album, 'title', '') or '')
            episode_list = getattr(album, 'episode_list', [])
            if isinstance(episode_list, list) and len(episode_list) > 0:
                task.progress.total_photos = len(episode_list)
            elif hasattr(album, '__len__'):
                task.progress.total_photos = len(album)
            # 估算总大小（每张图约 300KB）
            page_count = getattr(album, 'page_count', 0) or 0
            task.progress.total_mb = page_count * 0.3
            # 调用父类（触发插件等）
            super().before_album(album)

        def after_album(self, album):
            task.progress.percentage = 100.0
            task.progress.current_photo = task.progress.total_photos
            super().after_album(album)

        def before_photo(self, photo):
            task.progress.current_photo_name = (getattr(photo, 'name', '') or
                                                 getattr(photo, 'title', '') or '')
            # 从 photo 的所属 album 获取标题（单章下载时 before_album 不会被调用）
            if not task.progress.album_title:
                album = getattr(photo, 'from_album', None)
                if album:
                    task.progress.album_title = (getattr(album, 'name', '') or
                                                  getattr(album, 'title', '') or '')
            page_arr = getattr(photo, 'page_arr', [])
            if isinstance(page_arr, list):
                task.progress.total_images = len(page_arr)
            elif hasattr(photo, '__len__'):
                task.progress.total_images = len(photo)
            task.progress.current_image = 0
            # 单章下载时 total_photos 可能为 0，设为 1 让进度条正常工作
            if task.progress.total_photos == 0:
                task.progress.total_photos = 1
            task._last_bytes = 0
            task._last_time = time.time()
            self._check_cancel()
            super().before_photo(photo)

        def after_photo(self, photo):
            task.progress.current_photo += 1
            self._recalc_percentage()
            super().after_photo(photo)

        def before_image(self, image, img_save_path):
            self._check_cancel()
            super().before_image(image, img_save_path)

        def after_image(self, image, img_save_path):
            task.progress.current_image += 1
            # 计算已下载大小
            try:
                if os.path.exists(img_save_path):
                    file_size = os.path.getsize(img_save_path)
                    task._last_bytes += file_size
            except Exception:
                file_size = 0

            task.progress.downloaded_mb = task._last_bytes / (1024 * 1024)

            # 计算速度
            now = time.time()
            elapsed = now - task._last_time
            if elapsed > 0.5:
                speed = task._last_bytes / elapsed
                if speed > 1024 * 1024:
                    task.progress.download_speed = f'{speed / (1024 * 1024):.1f} MB/s'
                else:
                    task.progress.download_speed = f'{speed / 1024:.0f} KB/s'
                task._last_bytes = 0
                task._last_time = now

            self._recalc_percentage()
            super().after_image(image, img_save_path)

        def _recalc_percentage(self):
            if task.progress.total_photos > 0:
                photo_contrib = (task.progress.current_photo /
                                 task.progress.total_photos) * 100
                if task.progress.total_images > 0:
                    image_contrib = (task.progress.current_image /
                                     task.progress.total_images /
                                     task.progress.total_photos) * 100
                else:
                    image_contrib = 0
                task.progress.percentage = min(photo_contrib + image_contrib, 99.9)

        def _check_cancel(self):
            if task.cancel_event.is_set():
                raise DownloadCancelledException(f"下载 {task.task_id} 已被取消")

    return ProgressDownloader


class DownloadManager:
    """下载任务管理器"""

    def __init__(self, settings_provider):
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.Lock()
        self._settings = settings_provider
        self._queue = []  # 排队中的 task_id 列表
        self._max_parallel = 3  # 默认值，会被 settings 覆盖
        self._active_count = 0

    def _update_max_parallel(self):
        """从设置中读取最大并行数"""
        try:
            s = self._settings()
            self._max_parallel = int(s.get('max_parallel_downloads', 3) or 3)
        except Exception:
            self._max_parallel = 3
        if self._max_parallel < 1:
            self._max_parallel = 1

    def _try_start_next(self):
        """从队列中启动下一个等待任务"""
        with self._lock:
            while self._queue and self._active_count < self._max_parallel:
                next_id = self._queue.pop(0)
                task = self._tasks.get(next_id)
                if task and task.status == 'queued':
                    task.status = 'running'
                    task.start_time = time.time()
                    self._active_count += 1
                    thread = threading.Thread(
                        target=self._run_album_download if task.type == 'album' else self._run_photo_download,
                        args=(task, task.extras),
                        daemon=True
                    )
                    task._thread = thread
                    thread.start()

    def _on_task_done(self, task):
        """任务完成/失败/取消时释放槽位，启动下一个排队任务"""
        with self._lock:
            self._active_count = max(0, self._active_count - 1)
        self._try_start_next()

    def start_album_download(self, jm_id: str, extras: dict = None) -> str:
        self._update_max_parallel()
        task = DownloadTask(
            task_id=str(uuid.uuid4())[:8],
            type='album',
            jm_id=str(jm_id),
            extras=extras or {},
            status='queued',
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._queue.append(task.task_id)
        self._try_start_next()
        return task.task_id

    def start_photo_download(self, jm_id: str, extras: dict = None) -> str:
        self._update_max_parallel()
        task = DownloadTask(
            task_id=str(uuid.uuid4())[:8],
            type='photo',
            jm_id=str(jm_id),
            extras=extras or {},
            status='queued',
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._queue.append(task.task_id)
        self._try_start_next()
        return task.task_id

    def start_batch_download(self, jm_ids: list, dtype: str = 'album', extras: dict = None) -> list:
        task_ids = []
        for jm_id in jm_ids:
            if dtype == 'album':
                tid = self.start_album_download(jm_id, extras)
            else:
                tid = self.start_photo_download(jm_id, extras)
            task_ids.append(tid)
        return task_ids

    def _run_album_download(self, task: DownloadTask, extras: dict):
        from jmcomic import download_album
        from option_builder import build_option

        try:
            settings = self._settings()
            # 用不带 extra 的 option（ZIP 在下载后自己打包，更可靠）
            option = build_option(settings)
            ProgressDownloader = _make_progress_downloader(task)

            result = download_album(
                task.jm_id,
                option,
                downloader=ProgressDownloader,
                check_exception=False,
            )
            if result and len(result) >= 1:
                album_detail = result[0]
                task.save_path = self._get_save_path(option, album_detail)

            # 下载完成后自己打包 ZIP
            if settings.get('zip_enabled', True):
                try:
                    import logging
                    logging.getLogger('jmcomic').info(f'[ZIP] 开始为 JM{task.jm_id} 创建压缩包...')
                    zip_path = self._create_flat_zip(task, option, album_detail, settings)
                    if zip_path:
                        task.save_path = os.path.dirname(zip_path)
                        logging.getLogger('jmcomic').info(f'[ZIP] 完成: {zip_path}')
                except Exception as e:
                    logging.getLogger('jmcomic').error(f'[ZIP] 创建失败: {e}')
                    traceback.print_exc()

            task.status = 'completed'
            task.progress.percentage = 100.0
        except DownloadCancelledException:
            task.status = 'cancelled'
        except Exception as e:
            task.status = 'failed'
            task.error = f"{type(e).__name__}: {str(e)}"
            traceback.print_exc()
        finally:
            task.end_time = time.time()
            self._on_task_done(task)

    def _run_photo_download(self, task: DownloadTask, extras: dict):
        from jmcomic import download_photo
        from option_builder import build_option

        try:
            settings = self._settings()
            option = build_option(settings)
            ProgressDownloader = _make_progress_downloader(task)

            result = download_photo(
                task.jm_id,
                option,
                downloader=ProgressDownloader,
                check_exception=False,
            )
            if result and len(result) >= 1:
                photo_detail = result[0]
                task.save_path = self._get_save_path(option, photo_detail)

            # 下载完成后打包 ZIP
            if settings.get('zip_enabled', True):
                try:
                    import logging
                    log = logging.getLogger('jmcomic')
                    log.info(f'[ZIP] 开始为 JM{task.jm_id} 创建压缩包...')
                    # 用 photo 所属的 album 来创建 ZIP
                    zip_path = None
                    album = getattr(photo_detail, 'from_album', None)
                    if album:
                        zip_path = self._create_flat_zip(task, option, album, settings)
                    if zip_path:
                        task.save_path = os.path.dirname(zip_path)
                        log.info(f'[ZIP] 完成: {zip_path}')
                    else:
                        log.warning(f'[ZIP] 未能创建（album={bool(album)}）')
                except Exception as e:
                    logging.getLogger('jmcomic').error(f'[ZIP] 创建失败: {e}')
                    traceback.print_exc()

            task.status = 'completed'
            task.progress.percentage = 100.0
        except DownloadCancelledException:
            task.status = 'cancelled'
        except Exception as e:
            task.status = 'failed'
            task.error = f"{type(e).__name__}: {str(e)}"
            traceback.print_exc()
        finally:
            task.end_time = time.time()
            self._on_task_done(task)

    def _create_flat_zip(self, task: DownloadTask, option, album_detail, settings) -> str:
        """下载完成后创建扁平 ZIP 到 base_dir/zip/ 目录，解压后直接是图片"""
        import zipfile as zf
        import logging
        log = logging.getLogger('jmcomic')

        # 从 download_success_dict 获取实际保存路径
        album_dir = option.dir_rule.decide_album_root_dir(album_detail)
        log.info(f'[ZIP] album_dir={album_dir}, exists={os.path.isdir(album_dir)}')

        if not os.path.isdir(album_dir):
            # 回退：尝试从 option 直接推断
            base_dir = option.dir_rule.base_dir
            # 列出 base_dir 下最新的文件夹
            try:
                subdirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir)
                          if os.path.isdir(os.path.join(base_dir, d)) and d != 'zip']
                subdirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)
                if subdirs:
                    album_dir = subdirs[0]
                    log.info(f'[ZIP] fallback to: {album_dir}')
            except Exception:
                pass

        if not os.path.isdir(album_dir):
            log.warning(f'[ZIP] 找不到下载目录: {album_dir}')
            return None

        # 收集所有图片文件
        image_files = []
        for f in os.listdir(album_dir):
            path = os.path.join(album_dir, f)
            if os.path.isfile(path) and not f.endswith('.zip'):
                image_files.append(path)

        log.info(f'[ZIP] 找到 {len(image_files)} 个文件')
        if not image_files:
            return None

        # ZIP 文件名（清理非法字符）
        title = getattr(album_detail, 'name', '') or getattr(album_detail, 'title', '')
        aid = getattr(album_detail, 'album_id', task.jm_id)
        safe_title = title.replace('/', '_').replace('\\', '_').replace(':', '_') \
                          .replace('*', '_').replace('?', '_').replace('"', '_') \
                          .replace('<', '_').replace('>', '_').replace('|', '_')
        zip_name = f'[JM{aid}] {safe_title}.zip'

        # ZIP 放到 base_dir/zip/ 下
        base_dir = option.dir_rule.base_dir
        zip_dir = os.path.join(base_dir, 'zip')
        os.makedirs(zip_dir, exist_ok=True)
        zip_path = os.path.join(zip_dir, zip_name)

        # 创建扁平 ZIP
        with zf.ZipFile(zip_path, 'w', zf.ZIP_DEFLATED) as z:
            for img_path in image_files:
                z.write(img_path, os.path.basename(img_path))

        zip_size = os.path.getsize(zip_path)
        task.progress.downloaded_mb = zip_size / (1024 * 1024)
        log.info(f'[ZIP] 已创建: {zip_path} ({zip_size} bytes, {len(image_files)} 张图)')

        # 删除原始图片（如果设置要求）
        if settings.get('zip_delete_after', False):
            for img_path in image_files:
                try:
                    os.remove(img_path)
                except Exception:
                    pass
            try:
                remaining = [f for f in os.listdir(album_dir) if not f.endswith('.zip')]
                if not remaining:
                    os.rmdir(album_dir)
            except Exception:
                pass

        return zip_path

    def _get_save_path(self, option, detail) -> str:
        try:
            base_dir = getattr(option.dir_rule, 'base_dir', '')
            return str(base_dir)
        except Exception:
            return ''

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list:
        with self._lock:
            return list(self._tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task and task.status in ('pending', 'queued', 'running'):
            task.cancel_event.set()
            # 如果是排队中，直接从队列移除并标记取消
            if task.status == 'queued':
                with self._lock:
                    if task_id in self._queue:
                        self._queue.remove(task_id)
                task.status = 'cancelled'
                task.end_time = time.time()
                self._try_start_next()
            return True
        return False

    def clear_history(self) -> int:
        with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.status in ('completed', 'failed', 'cancelled')
            ]
            for tid in to_remove:
                del self._tasks[tid]
            return len(to_remove)
