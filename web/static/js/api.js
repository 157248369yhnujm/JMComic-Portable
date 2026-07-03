/**
 * API 层 — 所有与后端通信的 fetch 封装
 * 每个函数返回 Promise，成功时返回 data 部分，失败时抛出错误
 */

const BASE = '';

async function request(url, options = {}) {
    try {
        const resp = await fetch(BASE + url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        const json = await resp.json();
        if (!json.success) {
            throw new Error(json.error || '请求失败');
        }
        return json.data;
    } catch (e) {
        if (e.message && !e.message.includes('Failed to fetch')) {
            throw e;
        }
        throw new Error('无法连接到服务器，请确认服务器已启动');
    }
}

const api = {
    // ====== 搜索 ======
    search(params = {}) {
        const qs = new URLSearchParams();
        if (params.q) qs.set('q', params.q);
        if (params.type !== undefined) qs.set('type', params.type);
        if (params.page) qs.set('page', params.page);
        if (params.order) qs.set('order', params.order);
        if (params.time) qs.set('time', params.time);
        if (params.category) qs.set('category', params.category);
        if (params.sub_category) qs.set('sub_category', params.sub_category);
        return request(`/api/search?${qs.toString()}`);
    },

    // ====== 本子/章节详情 ======
    getAlbum(id) {
        return request(`/api/album/${id}`);
    },
    getPhoto(id) {
        return request(`/api/photo/${id}`);
    },

    // ====== 下载 ======
    startAlbumDownload(id, extras = {}) {
        return request(`/api/download/album/${id}`, {
            method: 'POST',
            body: JSON.stringify(extras),
        });
    },
    startPhotoDownload(id, extras = {}) {
        return request(`/api/download/photo/${id}`, {
            method: 'POST',
            body: JSON.stringify(extras),
        });
    },
    startBatchDownload(ids, type = 'album', extras = {}) {
        return request('/api/download/batch', {
            method: 'POST',
            body: JSON.stringify({ ids, type, ...extras }),
        });
    },
    getDownloadStatus(taskId) {
        return request(`/api/download/status/${taskId}`);
    },
    listDownloads() {
        return request('/api/download/list');
    },
    cancelDownload(taskId) {
        return request(`/api/download/cancel/${taskId}`, { method: 'POST' });
    },
    clearHistory() {
        return request('/api/download/history', { method: 'DELETE' });
    },

    // ====== 排行榜/分类 ======
    getRanking(type, page = 1, category = '0') {
        return request(`/api/ranking/${type}?page=${page}&category=${category}`);
    },
    getCategories(params = {}) {
        const qs = new URLSearchParams();
        if (params.page) qs.set('page', params.page);
        if (params.time) qs.set('time', params.time);
        if (params.category) qs.set('category', params.category);
        if (params.order) qs.set('order', params.order);
        if (params.sub_category) qs.set('sub_category', params.sub_category);
        return request(`/api/categories?${qs.toString()}`);
    },

    // ====== 收藏夹 ======
    login(username, password) {
        return request('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
    },
    loginStatus() {
        return request('/api/login/status');
    },
    logout() {
        return request('/api/logout', { method: 'POST' });
    },
    getFavorites(params = {}) {
        const qs = new URLSearchParams();
        if (params.page) qs.set('page', params.page);
        if (params.order_by) qs.set('order_by', params.order_by);
        if (params.folder_id) qs.set('folder_id', params.folder_id);
        return request(`/api/favorites?${qs.toString()}`);
    },
    addFavorite(albumId, folderId = '0') {
        return request(`/api/favorites/add/${albumId}`, {
            method: 'POST',
            body: JSON.stringify({ folder_id: folderId }),
        });
    },

    // ====== 设置 ======
    getSettings() {
        return request('/api/settings');
    },
    updateSettings(settings) {
        return request('/api/settings', {
            method: 'PUT',
            body: JSON.stringify(settings),
        });
    },
    testProxy(proxy) {
        return request('/api/settings/test-proxy', {
            method: 'POST',
            body: JSON.stringify({ proxy }),
        });
    },

    // ====== 封面图 ======
    getCdnDomain() {
        return request('/api/cdn-domain');
    },
    getCoverUrl(albumId) {
        return request(`/api/cover/${albumId}`);
    },
    batchCovers(ids) {
        return request('/api/batch-covers', {
            method: 'POST',
            body: JSON.stringify({ ids }),
        });
    },

    // ====== 本地漫画管理 ======
    getLocalAlbums() {
        return request('/api/local/albums');
    },
    getLocalAlbum(albumId) {
        return request(`/api/local/album/${albumId}`);
    },
    checkLocalPhoto(albumId, photoId) {
        return request(`/api/local/photo/${albumId}/${photoId}`);
    },
    // 纯本地预检：按 album_id 查 zip，零 JM API。返回 {has_local, mode, album_id, chapters}
    checkLocal(albumId) {
        return request(`/api/local/check/${albumId}`);
    },
};
