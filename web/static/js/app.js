/**
 * SPA 路由器 + 全局状态管理 + 导航栏 + Toast 通知 + 批量下载
 */

// 全局状态
let _cdnDomain = null;
let _coverCache = {};

// ========== 批量选择状态 ==========
let selectedIds = new Set();
let batchFetchAllFn = null;  // 当前页面的"获取全部ID"函数
let _pageNavPrevFn = null;   // 上一页回调
let _pageNavNextFn = null;   // 下一页回调
let _pageInfo = { current: 1, total: 1 };
let batchFetchPageFn = null; // 获取指定页ID的函数: (page) => [id, ...]

// ========== 页面选择器弹窗 ==========
function openPageModal() {
    const total = _pageInfo.total || 1;
    if (total <= 1) {
        showToast('只有一页，请直接用全选本页', 'info');
        return;
    }
    const grid = document.getElementById('page-select-grid');
    let html = '';
    for (let p = 1; p <= total; p++) {
        html += `<label><input type="checkbox" value="${p}"> 第${p}页</label>`;
    }
    grid.innerHTML = html;
    document.getElementById('page-select-modal').classList.add('show');
}

function closePageModal() {
    document.getElementById('page-select-modal').classList.remove('show');
}

function pageModalCheckAll() {
    document.querySelectorAll('#page-select-grid input[type=checkbox]').forEach(cb => cb.checked = true);
}

function pageModalClearAll() {
    document.querySelectorAll('#page-select-grid input[type=checkbox]').forEach(cb => cb.checked = false);
}

async function pageModalConfirm() {
    const checked = [...document.querySelectorAll('#page-select-grid input[type=checkbox]:checked')];
    if (checked.length === 0) {
        showToast('请至少勾选一页', 'warning');
        return;
    }
    if (!batchFetchPageFn) {
        showToast('当前页面不支持此项', 'warning');
        return;
    }

    closePageModal();
    const pages = checked.map(cb => parseInt(cb.value));
    showToast(`正在获取 ${pages.length} 页的作品ID...`, 'info');

    let totalAdded = 0;
    for (const p of pages) {
        try {
            const ids = await batchFetchPageFn(p);
            ids.forEach(id => selectedIds.add(id));
            totalAdded += ids.length;
        } catch (e) {}
    }
    updateBatchBar();
    // 刷新当前页可见的复选框
    document.querySelectorAll('.comic-card').forEach(card => {
        const id = card.dataset.id;
        const cb = card.querySelector('.comic-check');
        if (cb) cb.checked = selectedIds.has(id);
        card.classList.toggle('selected', selectedIds.has(id));
    });
    showToast(`已添加 ${totalAdded} 个作品（共 ${selectedIds.size} 个）`, 'success');
}

function setPageNav(prevFn, nextFn, current, total) {
    _pageNavPrevFn = prevFn;
    _pageNavNextFn = nextFn;
    _pageInfo = { current: current || 1, total: total || 1 };
    updatePageNavButtons();
}

function updatePageNavButtons() {
    const prevBtn = document.getElementById('page-nav-prev');
    const nextBtn = document.getElementById('page-nav-next');
    if (!prevBtn || !nextBtn) return;

    const show = _pageInfo.total > 1;
    prevBtn.style.display = show ? 'flex' : 'none';
    nextBtn.style.display = show ? 'flex' : 'none';

    if (show) {
        prevBtn.disabled = _pageInfo.current <= 1;
        nextBtn.disabled = _pageInfo.current >= _pageInfo.total;
        const hint = `${_pageInfo.current}/${_pageInfo.total}`;
        prevBtn.querySelector('.page-hint').textContent = hint;
        nextBtn.querySelector('.page-hint').textContent = hint;
    }
}

function pageNavPrev() {
    if (_pageNavPrevFn) _pageNavPrevFn();
}

function pageNavNext() {
    if (_pageNavNextFn) _pageNavNextFn();
}

function toggleSelect(albumId) {
    if (selectedIds.has(albumId)) {
        selectedIds.delete(albumId);
    } else {
        selectedIds.add(albumId);
    }
    updateBatchBar();
    document.querySelectorAll(`.comic-card[data-id="${albumId}"]`).forEach(c => {
        c.classList.toggle('selected', selectedIds.has(albumId));
    });
}

function selectAllCurrent() {
    document.querySelectorAll('.comic-card[data-id]').forEach(card => {
        const id = card.dataset.id;
        if (id) selectedIds.add(id);
        card.classList.add('selected');
        const cb = card.querySelector('.comic-check');
        if (cb) cb.checked = true;
    });
    updateBatchBar();
    showToast(`已选本页 ${selectedIds.size} 个`, 'info');
}

function clearSelection() {
    selectedIds.clear();
    document.querySelectorAll('.comic-card.selected').forEach(c => c.classList.remove('selected'));
    document.querySelectorAll('.comic-check').forEach(cb => cb.checked = false);
    updateBatchBar();
}

async function selectAll() {
    if (!batchFetchAllFn) return;
    showToast('正在获取全部作品ID...', 'info', 2000);
    try {
        const allIds = await batchFetchAllFn();
        allIds.forEach(id => selectedIds.add(id));
        updateBatchBar();
        document.querySelectorAll('.comic-card').forEach(card => {
            const id = card.dataset.id;
            if (selectedIds.has(id)) {
                card.classList.add('selected');
                const cb = card.querySelector('.comic-check');
                if (cb) cb.checked = true;
            }
        });
        showToast(`已选择全部 ${allIds.length} 个作品`, 'success');
    } catch (e) {
        showToast('获取失败: ' + e.message, 'error');
    }
}

async function batchDownload() {
    if (selectedIds.size === 0) return;
    const ids = [...selectedIds];
    try {
        await api.startBatchDownload(ids, 'album');
        showToast(`已启动 ${ids.length} 个下载任务`, 'success');
        clearSelection();
        updateDownloadBadge();
    } catch (e) {
        showToast('批量下载失败: ' + e.message, 'error');
    }
}

function updateBatchBar() {
    const bar = document.getElementById('batch-bar');
    const countEl = document.getElementById('batch-count');
    if (!bar) return;
    if (selectedIds.size > 0) {
        bar.classList.add('show');
        if (countEl) countEl.textContent = `已选 ${selectedIds.size} 个`;
    } else {
        bar.classList.remove('show');
    }
}

// 页面切换时隐藏翻页按钮
function hidePageNav() {
    document.getElementById('page-nav-prev').style.display = 'none';
    document.getElementById('page-nav-next').style.display = 'none';
    _pageNavPrevFn = null;
    _pageNavNextFn = null;
}

// ========== Toast 通知系统 ==========
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ========== 导航 ==========
function navigateTo(hash) {
    window.location.hash = hash;
}

function getCurrentPage() {
    const hash = window.location.hash.replace('#', '').split('?')[0];
    if (hash.startsWith('album/')) return 'album';
    return hash || 'home';
}

function getPageParam() {
    const hash = window.location.hash.replace('#', '').split('?')[0];
    if (hash.startsWith('album/')) return hash.replace('album/', '');
    return null;
}

function updateNavbar() {
    const page = getCurrentPage();
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === page);
    });
}

// ========== 登录状态检查 ==========
async function checkLoginStatus() {
    try {
        const status = await api.loginStatus();
        const loginBtn = document.getElementById('nav-login-btn');
        const userInfo = document.getElementById('nav-user-info');
        if (status.logged_in) {
            if (loginBtn) loginBtn.classList.add('hidden');
            if (userInfo) {
                userInfo.classList.remove('hidden');
                userInfo.textContent = '👤 ' + status.username;
            }
        } else {
            if (loginBtn) loginBtn.classList.remove('hidden');
            if (userInfo) userInfo.classList.add('hidden');
        }
    } catch (e) {
        // 静默
    }
}

// ========== CDN Domain 缓存 ==========
async function getCdnDomain() {
    if (_cdnDomain) return _cdnDomain;
    try {
        const data = await api.getCdnDomain();
        _cdnDomain = data.domain;
        return _cdnDomain;
    } catch (e) {
        return null;
    }
}

async function getCoverUrl(albumId) {
    if (_coverCache[albumId]) return _coverCache[albumId];
    try {
        const data = await api.getCoverUrl(albumId);
        const url = data.cover_url;
        _coverCache[albumId] = url;
        return url;
    } catch (e) {
        return null;
    }
}

// ========== 页面渲染调度 ==========
const pageRenderers = {
    home: renderDashboard,
    search: renderSearch,
    album: () => renderAlbum(getPageParam()),
    downloads: renderDownloads,
    ranking: renderRanking,
    favorites: renderFavorites,
    settings: renderSettings,
    local: renderLocal,
};

async function renderPage() {
    const main = document.getElementById('main-content');
    const page = getCurrentPage();
    const renderer = pageRenderers[page];

    updateNavbar();
    checkLoginStatus();

    if (!renderer) {
        main.innerHTML = `<div class="empty-state">
            <div class="icon">🔍</div>
            <p>页面不存在</p>
        </div>`;
        return;
    }

    main.innerHTML = `<div class="page-loading">
        <div class="spinner"></div>
        <p>加载中...</p>
    </div>`;

    try {
        await renderer();
    } catch (e) {
        main.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>页面加载失败: ${escapeHtml(e.message)}</p>
            <button class="btn btn-outline" style="margin-top:16px" onclick="renderPage()">重试</button>
        </div>`;
    }

    updateDownloadBadge();
}

// ========== 下载徽章更新 ==========
async function updateDownloadBadge() {
    try {
        const data = await api.listDownloads();
        const badge = document.getElementById('download-badge');
        if (data.active_count > 0) {
            badge.textContent = data.active_count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    } catch (e) { /* */ }
}

setInterval(updateDownloadBadge, 5000);

// ========== 工具函数 ==========
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatNumber(n) {
    if (!n) return '0';
    const num = parseInt(String(n).replace(/[^0-9]/g, ''));
    if (isNaN(num)) return String(n);
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

/**
 * 渲染漫画卡片网格（带封面图）
 */
function renderComicGrid(container, items, onClick) {
    if (!items || items.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <div class="icon">📭</div>
            <p>暂无数据</p>
        </div>`;
        return;
    }

    container.innerHTML = items.map((item, idx) => {
        const tags = (item.tags || []).slice(0, 3).map(t =>
            `<span class="tag">${escapeHtml(typeof t === 'string' ? t : t.name || '')}</span>`
        ).join('');

        const coverId = item.album_id;
        const checked = selectedIds.has(item.album_id) ? 'checked' : '';
        const selClass = selectedIds.has(item.album_id) ? ' selected' : '';
        const placeholder = `<div class="comic-cover" data-cover-id="${escapeHtml(coverId)}">
            <span style="font-size:2.5rem;opacity:0.3">📚</span>
        </div>`;

        return `
        <div class="comic-card${selClass}" data-id="${escapeHtml(item.album_id)}">
            <input type="checkbox" class="comic-check" ${checked} data-id="${escapeHtml(item.album_id)}">
            ${placeholder}
            <div class="comic-info">
                <div class="comic-title">${escapeHtml(item.name || item.title || '未知')}</div>
                <div class="comic-meta">${tags}</div>
                <div class="comic-stats">
                    <span>👁 ${formatNumber(item.views)}</span>
                    <span>❤ ${formatNumber(item.likes)}</span>
                </div>
            </div>
        </div>`;
    }).join('');

    // 复选框事件
    container.querySelectorAll('.comic-check').forEach(cb => {
        cb.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSelect(cb.dataset.id);
        });
    });

    // 点击卡片其他区域跳转详情
    container.querySelectorAll('.comic-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.classList.contains('comic-check')) return;
            const id = card.dataset.id;
            if (onClick) onClick(id);
        });
    });

    // 延迟加载封面图
    loadCoverImages(container);
}

/**
 * 延迟加载封面图
 */
async function loadCoverImages(container, retry = 0) {
    const covers = container.querySelectorAll('.comic-cover[data-cover-id], .album-cover-large[data-cover-id]');
    if (covers.length === 0) return;

    const ids = [...covers].map(el => el.dataset.coverId).filter(Boolean);
    if (ids.length === 0) return;

    try {
        const data = await api.batchCovers(ids);
        const coverMap = data.covers || {};

        for (const el of covers) {
            const url = coverMap[el.dataset.coverId];
            if (url) {
                el.innerHTML = `<img src="${escapeHtml(url)}" loading="lazy"
                    onerror="this.innerHTML='<span style=\\'font-size:2.5rem;opacity:0.3\\'>📚</span>'">`;
            }
        }
    } catch (e) {
        // CDN 域名可能还未就绪，3秒后重试一次
        if (retry < 2) {
            setTimeout(() => loadCoverImages(container, retry + 1), 3000);
        }
    }
}

/**
 * 渲染分页控件
 */
function renderPagination(container, currentPage, totalPages, onPageChange) {
    // 设置左右固定翻页按钮
    if (totalPages > 1) {
        setPageNav(
            () => { if (currentPage > 1) onPageChange(currentPage - 1); },
            () => { if (currentPage < totalPages) onPageChange(currentPage + 1); },
            currentPage, totalPages
        );
    } else {
        hidePageNav();
    }

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';
    html += `<button ${currentPage <= 1 ? 'disabled' : ''} data-page="${currentPage - 1}">上一页</button>`;

    const maxButtons = 7;
    let start = Math.max(1, currentPage - 3);
    let end = Math.min(totalPages, start + maxButtons - 1);
    if (end - start < maxButtons - 1) {
        start = Math.max(1, end - maxButtons + 1);
    }

    if (start > 1) {
        html += `<button data-page="1">1</button>`;
        if (start > 2) html += `<span class="page-info">...</span>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    if (end < totalPages) {
        if (end < totalPages - 1) html += `<span class="page-info">...</span>`;
        html += `<button data-page="${totalPages}">${totalPages}</button>`;
    }

    html += `<button ${currentPage >= totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">下一页</button>`;
    html += `<span class="page-info">共 ${totalPages} 页</span>`;

    container.innerHTML = html;

    container.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = parseInt(btn.dataset.page);
            if (page && onPageChange) onPageChange(page);
        });
    });
}

// ========== 路由监听 ==========
window.addEventListener('hashchange', renderPage);
window.addEventListener('load', () => {
    renderPage();
    checkLoginStatus();
});
