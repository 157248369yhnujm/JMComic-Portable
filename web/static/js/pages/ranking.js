/**
 * 排行榜页面 — 最新 / 最多爱心 / 总排行 / 月排行 / 周排行 / 日排行
 */
let rankingState = { type: 'latest', page: 1, category: '0' };
let _rankingLoadId = 0;  // 防止竞态条件：快速切换标签时丢弃过期响应

async function renderRanking() {
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="page-header">
            <h1>🏆 排行榜</h1>
        </div>

        <!-- 操作栏 -->
        <div class="page-toolbar" id="ranking-toolbar" style="display:none">
            <button class="btn btn-sm btn-outline" onclick="selectAll()">全选所有页</button>
            <span style="color:var(--text-secondary);font-size:0.85rem">勾选作品后点击批量下载</span>
        </div>

        <!-- 排行榜类型标签 -->
        <div class="tabs" id="ranking-tabs">
            <button class="tab-btn active" data-type="latest">最新</button>
            <button class="tab-btn" data-type="most_liked">最多爱心</button>
            <button class="tab-btn" data-type="all_time">总排行</button>
            <button class="tab-btn" data-type="monthly">月排行</button>
            <button class="tab-btn" data-type="weekly">周排行</button>
            <button class="tab-btn" data-type="daily">日排行</button>
        </div>

        <!-- 分类过滤 -->
        <div class="search-bar" style="margin-bottom:16px">
            <select id="ranking-category">
                <option value="0">全部分类</option>
                <option value="doujin">同人</option>
                <option value="single">单行本</option>
                <option value="short">短篇</option>
                <option value="another">其他</option>
                <option value="hanman">韩漫</option>
                <option value="meiman">美漫</option>
                <option value="3D">3D</option>
                <option value="english_site">英文站</option>
            </select>
            <button class="btn btn-primary" id="ranking-load-btn">加载</button>
        </div>

        <div id="ranking-results">
            <div class="page-loading"><div class="spinner"></div></div>
        </div>
        <div id="ranking-pagination"></div>
    `;

    // 事件绑定
    document.querySelectorAll('#ranking-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            rankingState.type = btn.dataset.type;
            rankingState.page = 1;
            document.querySelectorAll('#ranking-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadRanking();
        });
    });

    batchFetchAllFn = fetchAllRankingIds;
    batchFetchPageFn = fetchRankingPageIds;
    document.getElementById('ranking-load-btn').addEventListener('click', () => {
        rankingState.category = document.getElementById('ranking-category').value;
        rankingState.page = 1;
        loadRanking();
    });

    loadRanking();
}

async function loadRanking(page = 1) {
    if (page) rankingState.page = page;

    // 递增请求 ID，后续检查防止过期响应覆盖当前页面
    const myLoadId = ++_rankingLoadId;

    const resultsDiv = document.getElementById('ranking-results');
    const paginationDiv = document.getElementById('ranking-pagination');

    resultsDiv.innerHTML = `<div class="page-loading"><div class="spinner"></div></div>`;
    paginationDiv.innerHTML = '';

    try {
        const data = await api.getRanking(rankingState.type, rankingState.page, rankingState.category);

        // 如果在这期间用户切换了标签或页码，丢弃此响应
        if (myLoadId !== _rankingLoadId) return;

        const items = data.items || [];
        rankingState.page_count = data.page_count || 1;

        resultsDiv.innerHTML = `<div class="comic-grid" id="ranking-comic-grid"></div>`;

        document.getElementById('ranking-toolbar').style.display = 'flex';
        if (items.length > 0) {
            const grid = document.getElementById('ranking-comic-grid');
            renderComicGrid(grid, items, (id) => {
                navigateTo(`#album/${id}`);
            });
        } else {
            resultsDiv.innerHTML = `<div class="empty-state"><p>暂无数据</p></div>`;
        }

        renderPagination(paginationDiv, rankingState.page, data.page_count || 1, (p) => {
            rankingState.page = p;
            loadRanking(p);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    } catch (e) {
        if (myLoadId !== _rankingLoadId) return;
        resultsDiv.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>${escapeHtml(e.message)}</p>
            <button class="btn btn-outline" style="margin-top:12px" onclick="loadRanking()">重试</button>
        </div>`;
    }
}


async function fetchAllRankingIds() {
    const allIds = [];
    const totalPages = rankingState.page_count || 1;
    for (let p = 1; p <= totalPages; p++) {
        try {
            const data = await api.getRanking(rankingState.type, p, rankingState.category);
            for (const item of (data.items || [])) {
                allIds.push(item.album_id);
            }
        } catch (e) {}
    }
    return allIds;
}


async function fetchRankingPageIds(page) {
    try {
        const data = await api.getRanking(rankingState.type, page, rankingState.category);
        return (data.items || []).map(item => item.album_id);
    } catch (e) { return []; }
}
