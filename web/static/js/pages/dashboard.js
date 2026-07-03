/**
 * 首页仪表盘 — 快速下载 + 排行榜速览
 */
let _dashLoadId = 0;  // 防止竞态条件

async function renderDashboard() {
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="page-header">
            <h1>🏠 JM漫画下载器</h1>
            <p>搜索、浏览、下载禁漫本子 — 全部在浏览器中完成</p>
        </div>

        <!-- 快速下载 -->
        <div class="quick-download">
            <h3>⚡ 快速下载</h3>
            <div class="quick-download-form">
                <input type="text" id="quick-id" placeholder="输入本子ID（如 123456）或章节ID（如 p123456）">
                <button class="btn btn-primary" id="quick-dl-btn">立即下载</button>
            </div>
            <div style="margin-top:8px;font-size:0.8rem;color:var(--text-secondary)">
                支持批量：用逗号分隔多个ID，如 123,456,789
            </div>
        </div>

        <!-- 排行榜速览 -->
        <div class="page-header" style="margin-top:8px">
            <h2>🔥 排行榜速览</h2>
        </div>
        <div class="tabs" id="dash-tabs">
            <button class="tab-btn active" data-tab="latest">最新</button>
            <button class="tab-btn" data-tab="most_liked">最多爱心</button>
            <button class="tab-btn" data-tab="all_time">总排行</button>
            <button class="tab-btn" data-tab="monthly">月排行</button>
            <button class="tab-btn" data-tab="weekly">周排行</button>
            <button class="tab-btn" data-tab="daily">日排行</button>
        </div>
        <div id="dash-ranking-content">
            <div class="page-loading"><div class="spinner"></div></div>
        </div>
    `;

    // 快速下载按钮
    document.getElementById('quick-dl-btn').addEventListener('click', async () => {
        const input = document.getElementById('quick-id').value.trim();
        if (!input) {
            showToast('请输入本子ID或章节ID', 'warning');
            return;
        }

        const ids = input.split(/[,，\s]+/).filter(Boolean);
        const albumIds = [];
        const photoIds = [];

        for (const raw of ids) {
            if (raw.toLowerCase().startsWith('p')) {
                photoIds.push(raw.slice(1));
            } else {
                albumIds.push(raw);
            }
        }

        if (albumIds.length === 0 && photoIds.length === 0) {
            showToast('未识别到有效ID', 'warning');
            return;
        }

        try {
            if (albumIds.length === 1 && photoIds.length === 0) {
                await api.startAlbumDownload(albumIds[0]);
                showToast(`已开始下载本子 JM${albumIds[0]}`, 'success');
            } else if (photoIds.length === 1 && albumIds.length === 0) {
                await api.startPhotoDownload(photoIds[0]);
                showToast(`已开始下载章节 JM${photoIds[0]}`, 'success');
            } else {
                const tasks = [];
                for (const aid of albumIds) {
                    tasks.push(api.startAlbumDownload(aid));
                }
                for (const pid of photoIds) {
                    tasks.push(api.startPhotoDownload(pid));
                }
                await Promise.all(tasks);
                showToast(`已启动 ${tasks.length} 个下载任务`, 'success');
            }

            document.getElementById('quick-id').value = '';
            updateDownloadBadge();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    document.getElementById('quick-id').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('quick-dl-btn').click();
        }
    });

    // 排行榜标签页
    let currentTab = 'latest';
    document.querySelectorAll('#dash-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentTab = btn.dataset.tab;
            document.querySelectorAll('#dash-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadDashRanking(currentTab);
        });
    });

    loadDashRanking('latest');
}

async function loadDashRanking(type) {
    const myLoadId = ++_dashLoadId;
    const container = document.getElementById('dash-ranking-content');
    try {
        const data = await api.getRanking(type, 1, '0');
        if (myLoadId !== _dashLoadId) return;

        const items = (data.items || []).slice(0, 8);
        if (items.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>暂无数据</p></div>`;
            return;
        }

        container.innerHTML = `<div class="comic-grid" id="dash-comic-grid"></div>`;
        const grid = document.getElementById('dash-comic-grid');
        renderComicGrid(grid, items, (id) => {
            navigateTo(`#album/${id}`);
        });
    } catch (e) {
        if (myLoadId !== _dashLoadId) return;
        container.innerHTML = `<div class="empty-state">
            <p>加载失败: ${escapeHtml(e.message)}</p>
            <button class="btn btn-outline" style="margin-top:12px" onclick="loadDashRanking('${type}')">重试</button>
        </div>`;
    }
}
