/**
 * 搜索页面 — 完整的搜索功能，支持所有筛选条件
 */
let searchState = { q: '', type: 0, page: 1, order: 'mr', time: 'a', category: '', sub_category: '' };

async function renderSearch() {
    const main = document.getElementById('main-content');

    // 从 URL 恢复搜索参数
    const hash = window.location.hash;
    const searchParams = new URLSearchParams(hash.includes('?') ? hash.split('?')[1] : '');

    main.innerHTML = `
        <div class="page-header">
            <h1>🔍 搜索本子</h1>
        </div>

        <!-- 操作栏 -->
        <div class="page-toolbar" id="search-toolbar" style="display:none">
            <button class="btn btn-sm btn-outline" onclick="selectAll()">全选所有页</button>
            <span style="color:var(--text-secondary);font-size:0.85rem">勾选作品后点击批量下载</span>
        </div>

        <!-- 搜索栏 -->
        <div class="search-bar">
            <input type="text" id="search-q" placeholder="全彩 +人妻 (包含) | 全彩 -人妻 (排除) | 全彩 人妻 (任意)…" value="${escapeHtml(searchParams.get('q') || '')}">
            <select id="search-type">
                <option value="0">站点搜索</option>
                <option value="1">搜索作品</option>
                <option value="2">搜索作者</option>
                <option value="3">搜索标签</option>
                <option value="4">搜索角色</option>
            </select>
            <select id="search-order">
                <option value="mr">最新</option>
                <option value="mv">最多观看</option>
                <option value="mp">最多图片</option>
                <option value="tf">最多喜欢</option>
            </select>
            <select id="search-time">
                <option value="a">全部时间</option>
                <option value="t">今天</option>
                <option value="w">本周</option>
                <option value="m">本月</option>
            </select>
            <button class="btn btn-primary" id="search-btn">搜索</button>
        </div>
        <div style="color:var(--text-secondary);font-size:0.8rem;margin-top:4px">
            💡 高级语法：<code>全彩 +人妻</code> 包含全部 | <code>全彩 -人妻</code> 排除 | <code>全彩 人妻</code> 任意
        </div>

        <!-- 搜索结果 -->
        <div id="search-results">
            <div class="empty-state">
                <div class="icon">🔎</div>
                <p>输入关键词开始搜索</p>
            </div>
        </div>
        <div id="search-pagination"></div>
    `;

    // 事件绑定
    document.getElementById('search-btn').addEventListener('click', () => doSearch());
    document.getElementById('search-q').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doSearch();
    });

    // 显示工具栏
    batchFetchAllFn = fetchAllSearchIds;
    batchFetchPageFn = fetchSearchPageIds;

    // 如果有 URL 参数，自动搜索
    if (searchParams.get('q')) {
        document.getElementById('search-type').value = searchParams.get('type') || '0';
        document.getElementById('search-order').value = searchParams.get('order') || 'mr';
        document.getElementById('search-time').value = searchParams.get('time') || 'a';
        doSearch();
    }
}

async function doSearch(page = 1) {
    const q = document.getElementById('search-q').value.trim();
    if (!q) {
        showToast('请输入搜索关键词', 'warning');
        return;
    }

    searchState = {
        q: q,
        type: parseInt(document.getElementById('search-type').value),
        page: page,
        order: document.getElementById('search-order').value,
        time: document.getElementById('search-time').value,
    };

    const resultsDiv = document.getElementById('search-results');
    const paginationDiv = document.getElementById('search-pagination');

    resultsDiv.innerHTML = `<div class="page-loading"><div class="spinner"></div><p>搜索中...</p></div>`;
    paginationDiv.innerHTML = '';

    try {
        const data = await api.search(searchState);
        const items = data.items || [];
        searchState.page_count = data.page_count || 1;
        searchState.total = data.total || 0;

        resultsDiv.innerHTML = `<div class="comic-grid" id="search-comic-grid"></div>
            <div style="margin-top:12px;color:var(--text-secondary);font-size:0.85rem">
                共 ${data.total || 0} 个结果，第 ${data.current_page || 1}/${data.page_count || 1} 页
            </div>`;

        document.getElementById('search-toolbar').style.display = 'flex';
        if (items.length > 0) {
            const grid = document.getElementById('search-comic-grid');
            renderComicGrid(grid, items, (id) => {
                navigateTo(`#album/${id}`);
            });
        }

        // 分页
        renderPagination(paginationDiv, searchState.page, data.page_count || 1, (p) => {
            searchState.page = p;
            doSearch(p);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    } catch (e) {
        resultsDiv.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>${escapeHtml(e.message)}</p>
            <button class="btn btn-outline" style="margin-top:12px" onclick="doSearch(${searchState.page})">重试</button>
        </div>`;
    }
}


async function fetchAllSearchIds() {
    const allIds = [];
    const totalPages = searchState.page_count || 1;
    for (let p = 1; p <= totalPages; p++) {
        try {
            const data = await api.search({...searchState, page: p});
            for (const item of (data.items || [])) {
                allIds.push(item.album_id);
            }
        } catch (e) {
            // skip failed pages
        }
    }
    return allIds;
}


async function fetchSearchPageIds(page) {
    try {
        const data = await api.search({...searchState, page: page});
        return (data.items || []).map(item => item.album_id);
    } catch (e) { return []; }
}
