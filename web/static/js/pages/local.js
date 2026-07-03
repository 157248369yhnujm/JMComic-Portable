/**
 * 本地漫画管理页面 — 完全离线可用
 * 所有漫画点击进入本地详情页（章节列表），无需 JM API
 */

let _localSort = { field: 'mtime', asc: false };
let _localAlbums = [];

async function renderLocal() {
    const main = document.getElementById('main-content');
    hidePageNav(); clearSelection();
    main.innerHTML = `<div class="page-loading"><div class="spinner"></div><p>正在扫描本地漫画...</p></div>`;

    try {
        const data = await api.getLocalAlbums();
        _localAlbums = data.albums || [];
        window._localAlbumsForReader = _localAlbums;  // 供阅读器随机下一本用
        if (_localAlbums.length === 0) {
            main.innerHTML = `<div class="page-header"><h1>📂 本地漫画</h1></div>
            <div class="empty-state"><div class="icon">📭</div><p>本地还没有下载任何漫画</p>
            <p style="font-size:0.85rem;color:var(--text-muted);margin-top:8px">去 <a href="#search" style="color:var(--accent)">搜索</a> 或 <a href="#ranking" style="color:var(--accent)">排行榜</a> 下载漫画吧</p></div>`;
            return;
        }
        renderLocalGrid();
    } catch (e) {
        main.innerHTML = `<div class="page-header"><h1>📂 本地漫画</h1></div>
        <div class="empty-state"><div class="icon">❌</div><p>加载失败: ${escapeHtml(e.message)}</p>
        <button class="btn btn-outline" style="margin-top:16px" onclick="renderLocal()">重试</button></div>`;
    }
}

function renderLocalGrid() {
    const albums = _localAlbums;
    const totalImages = albums.reduce((s, a) => s + (a.image_count || 0), 0);
    const totalSize = albums.reduce((s, a) => s + (a.total_size_mb || 0), 0);
    const zipOnlyCount = albums.filter(a => a.zip_only).length;
    const sizeStr = totalSize >= 1024 ? (totalSize / 1024).toFixed(1) + ' GB' : totalSize.toFixed(0) + ' MB';

    const main = document.getElementById('main-content');
    let html = `<div class="page-header"><h1>📂 本地漫画</h1><p>共 ${albums.length} 部 · ${totalImages} 张图 · ${sizeStr}</p></div>`;
    html += renderSortToolbar(albums.length - zipOnlyCount, zipOnlyCount);

    const sorted = sortAlbums(albums, _localSort.field, _localSort.asc);
    html += `<div class="comic-grid" id="local-grid">${sorted.map(a => renderAlbumCard(a)).join('')}</div>`;
    main.innerHTML = html;
    bindSortButtons();
}

// ==================== 排序 ====================

function sortAlbums(albums, field, asc) {
    return [...albums].sort((a, b) => {
        let va, vb;
        switch (field) {
            case 'name':
                va = (a.album_title || '').toLowerCase(); vb = (b.album_title || '').toLowerCase();
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            case 'mtime':
                va = a.mtime || 0; vb = b.mtime || 0;
                return asc ? va - vb : vb - va;
            case 'images':
                va = a.image_count || 0; vb = b.image_count || 0;
                return asc ? va - vb : vb - va;
            default: return 0;
        }
    });
}

function renderSortToolbar(dirs, zips) {
    const fields = [
        { key: 'mtime',  label: '⏱ 时间' },
        { key: 'name',   label: '📛 名称' },
        { key: 'images', label: '🖼 图片数' },
    ];
    let btns = '';
    for (const f of fields) {
        const active = _localSort.field === f.key;
        const arrow = active ? (_localSort.asc ? ' ▲' : ' ▼') : '';
        btns += `<button class="btn btn-sm ${active ? 'btn-primary' : 'btn-outline'}" data-sort="${f.key}">${f.label}${arrow}</button>`;
    }
    return `<div class="page-toolbar">
        <button class="btn btn-sm btn-outline" onclick="renderLocal()">🔄 刷新</button>
        <span style="color:var(--border);margin:0 4px">|</span>${btns}
        <span style="color:var(--text-muted);font-size:0.8rem;margin-left:auto">${dirs}目录${zips>0?' · '+zips+'ZIP':''}</span>
    </div>`;
}

function bindSortButtons() {
    document.querySelectorAll('[data-sort]').forEach(btn => {
        btn.addEventListener('click', () => {
            const field = btn.dataset.sort;
            _localSort.asc = (_localSort.field === field) ? !_localSort.asc : false;
            _localSort.field = field;
            renderLocalGrid();
        });
    });
}

// ==================== 卡片 ====================

function renderAlbumCard(a) {
    const coverUrl = a.album_id
        ? `/api/local/cover/${a.album_id}`
        : `/api/local/dir-cover?name=${encodeURIComponent(a.album_title)}`;

    const sizeStr = a.total_size_mb >= 1024 ? (a.total_size_mb/1024).toFixed(1)+'GB' : a.total_size_mb.toFixed(0)+'MB';

    let statusHtml, statusLabel;
    if (a.zip_only)      { statusHtml = '📦 ZIP'; statusLabel = 'zip'; }
    else if (a.has_zip)  { statusHtml = '📦+📁'; statusLabel = 'both'; }
    else                 { statusHtml = '📁 图片'; statusLabel = 'dir'; }

    let timeStr = '';
    if (a.mtime) {
        const d = new Date(a.mtime * 1000);
        timeStr = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    }

    const idTag = a.album_id ? `JM${escapeHtml(a.album_id)}` : '';

    // 把所有数据塞到 dataset 中，点击时离线可用
    const chaps = (a.chapter_prefixes || []).join(',');
    const chapCounts = JSON.stringify(a.chapter_counts || {});

    return `<div class="comic-card" style="cursor:pointer"
        onclick="showLocalDetail(this)" title="${escapeHtml(a.album_title)}"
        data-title="${escapeHtml(a.album_title)}"
        data-album-id="${escapeHtml(a.album_id||'')}"
        data-zip-only="${a.zip_only?'1':'0'}"
        data-image-count="${a.image_count||0}"
        data-chapter-count="${a.chapter_count||0}"
        data-size="${sizeStr}"
        data-mtime="${timeStr}"
        data-chapters="${escapeHtml(chaps)}"
        data-chap-counts="${escapeHtml(chapCounts)}">
        <div class="comic-cover">
            <img src="${coverUrl}" loading="lazy"
                onerror="this.parentElement.innerHTML='<span style=\\'font-size:2.5rem;opacity:0.3\\'>📚</span>'"
                style="width:100%;height:100%;object-fit:cover">
        </div>
        <div class="comic-info">
            <div class="comic-title">${escapeHtml(a.album_title)}</div>
            <div class="comic-meta">
                <span class="tag" style="background:var(--info);color:#fff">${statusHtml}</span>
                ${idTag ? `<span class="tag">${idTag}</span>` : ''}
            </div>
            <div class="comic-stats">
                <span>🖼 ${a.image_count||'?'}张</span>
                <span>📖 ${a.chapter_count||'?'}章</span>
                <span>💾 ${sizeStr}</span>
                ${timeStr ? `<span style="font-size:0.65rem;color:var(--text-muted)">${timeStr}</span>` : ''}
            </div>
        </div>
    </div>`;
}

// ==================== 本地详情页（完全离线可用） ====================

function showLocalDetail(card) {
    const info = {
        title:       card.dataset.title,
        albumId:     card.dataset.albumId,
        zipOnly:     card.dataset.zipOnly === '1',
        imageCount:  parseInt(card.dataset.imageCount) || 0,
        chapterCount: parseInt(card.dataset.chapterCount) || 0,
        size:        card.dataset.size,
        mtime:       card.dataset.mtime,
        chapters:    card.dataset.chapters ? card.dataset.chapters.split(',').filter(Boolean) : [],
        chapCounts:  {},
    };
    try { info.chapCounts = JSON.parse(card.dataset.chapCounts || '{}'); } catch(e) {}

    const main = document.getElementById('main-content');
    hidePageNav(); clearSelection();

    const coverUrl = info.albumId
        ? `/api/local/cover/${info.albumId}`
        : `/api/local/dir-cover?name=${encodeURIComponent(info.title)}`;

    // 构建章节列表（离线数据，无需API）
    let chaptersHtml = '';
    const chapList = info.zipOnly ? info.chapters : (info.chapters.length > 0 ? info.chapters : ['001']);

    chaptersHtml = `<h3 style="font-size:1rem;margin:16px 0 8px">📑 章节目录 (${chapList.length})</h3>
    <div style="display:flex;flex-direction:column;gap:4px;max-height:400px;overflow-y:auto">`;

    for (const ch of chapList) {
        const count = info.chapCounts[ch] || 0;
        const chIdx = parseInt(ch) || 0;
        chaptersHtml += `<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 14px;background:var(--bg-card);border-radius:var(--radius-sm);cursor:pointer"
            onmouseenter="this.style.background='var(--bg-card-hover)'"
            onmouseleave="this.style.background='var(--bg-card)'"
            onclick="openLocalChapter(this)" data-chapter="${escapeHtml(ch)}">
            <span style="font-size:0.9rem;font-weight:500">第${chIdx}章</span>
            <span style="font-size:0.8rem;color:var(--text-secondary)">${count > 0 ? count + ' 张' : ''}</span>
        </div>`;
    }
    chaptersHtml += `</div>`;

    // 状态标签
    let statusLabel;
    if (info.zipOnly) statusLabel = '📦 ZIP 压缩包';
    else if (chapList.length > 0) statusLabel = '📁 图片文件夹';
    else statusLabel = '📦 压缩包';

    main.innerHTML = `<div class="page-header">
        <button class="btn btn-outline btn-sm" onclick="renderLocalGrid()">← 返回</button>
        ${info.albumId ? `<a href="#album/${escapeHtml(info.albumId)}" style="margin-left:8px;font-size:0.85rem;color:var(--accent)">🌐 在线详情</a>` : ''}
    </div>

    <div class="album-detail">
        <div>
            <div class="album-cover-large">
                <img src="${coverUrl}" style="width:100%;height:100%;object-fit:cover"
                    onerror="this.parentElement.innerHTML='<span style=\\'font-size:4rem;opacity:0.2\\'>📚</span>'">
            </div>
            <div style="margin-top:12px;display:flex;flex-direction:column;gap:8px">
                ${chapList.length > 0 ? `<button class="btn btn-primary btn-block" onclick="document.querySelector('[data-chapter]').click()">👀 从第1章开始阅读</button>` : ''}
            </div>
        </div>

        <div class="album-info-section">
            <h1 class="album-title">${escapeHtml(info.title)}</h1>
            <div class="stats-row">
                <span class="stat-item">🖼 ${info.imageCount || '?'} 张图片</span>
                <span class="stat-item">📖 ${info.chapterCount || chapList.length || '?'} 章</span>
                <span class="stat-item">💾 ${info.size || '?'}</span>
                ${info.mtime ? `<span class="stat-item">📅 ${info.mtime}</span>` : ''}
            </div>
            <div class="tags-container" style="margin-top:8px">
                <span class="tag-badge">${statusLabel}</span>
                ${info.albumId ? `<span class="tag-badge" style="background:var(--accent-glow);color:var(--accent)">JM${escapeHtml(info.albumId)}</span>` : ''}
            </div>
            ${chaptersHtml}
        </div>
    </div>`;

    // 把关键数据挂到 main 上，供 openLocalChapter 读取
    main._localInfo = info;
}

/**
 * 打开本地章节 — 纯本地操作，无需联网
 */
function openLocalChapter(el) {
    const info = document.getElementById('main-content')._localInfo;
    if (!info) return;

    const chapter = el.dataset.chapter;
    const encodedTitle = encodeURIComponent(info.title);
    const allChapters = Object.keys(info.chapCounts).length > 0
        ? Object.keys(info.chapCounts).join(',')
        : (info.chapters.join(',') || chapter);

    if (info.zipOnly && info.albumId) {
        window.open(`/reader?dir=zip:${info.albumId}&chapter=${chapter}&chapters=${allChapters}`, '_blank');
    } else {
        window.open(`/reader?dir=${encodedTitle}&chapter=${chapter}&chapters=${allChapters}`, '_blank');
    }
}
