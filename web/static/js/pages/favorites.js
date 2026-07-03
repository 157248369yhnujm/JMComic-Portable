/**
 * 收藏夹页面 — 登录、查看收藏、导出
 */
let favoritesState = { page: 1, folder_id: '0', order_by: 'mr' };

async function renderFavorites() {
    const main = document.getElementById('main-content');

    // 检查登录状态
    let loggedIn = false;
    let username = '';
    try {
        const status = await api.loginStatus();
        loggedIn = status.logged_in;
        username = status.username;
    } catch (e) { /* ignore */ }

    main.innerHTML = `
        <div class="page-header">
            <h1>⭐ 收藏夹</h1>
            <p>${loggedIn ? `已登录: ${escapeHtml(username)}` : '需要登录后才能查看收藏夹'}</p>
        </div>

        ${!loggedIn ? `
        <div class="card login-card">
            <h3 style="margin-bottom:16px">🔑 登录禁漫</h3>
            <div class="form-group">
                <label>用户名</label>
                <input type="text" id="login-username" placeholder="输入你的禁漫用户名">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="login-password" placeholder="输入密码">
            </div>
            <button class="btn btn-primary btn-block" id="login-btn">登录</button>
        </div>
        ` : `
        <div style="margin-bottom:16px;display:flex;gap:8px">
            <button class="btn btn-primary btn-sm" id="load-fav-btn">🔄 刷新收藏</button>
            <button class="btn btn-outline btn-sm" id="select-all-fav-btn">☑ 全选所有页</button>
            <button class="btn btn-outline btn-sm" id="logout-btn">退出登录</button>
        </div>
        <div class="search-bar" style="margin-bottom:16px">
            <select id="fav-folder">
                <option value="0">全部收藏</option>
            </select>
            <select id="fav-order">
                <option value="mr">最新</option>
                <option value="mv">最多观看</option>
            </select>
        </div>
        `}

        <div id="fav-content">
            ${!loggedIn ? '' : '<div class="page-loading"><div class="spinner"></div></div>'}
        </div>
        <div id="fav-pagination"></div>
    `;

    if (!loggedIn) {
        // 登录按钮
        const doLogin = async () => {
            const username = document.getElementById('login-username').value.trim();
            const password = document.getElementById('login-password').value.trim();
            if (!username || !password) {
                showToast('请输入用户名和密码', 'warning');
                return;
            }
            try {
                await api.login(username, password);
                showToast('登录成功！', 'success');
                renderFavorites();
            } catch (e) {
                showToast(e.message, 'error');
            }
        };

        document.getElementById('login-btn').addEventListener('click', doLogin);

        // 回车登录
        document.getElementById('login-password').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('login-btn').click();
        });
    } else {
        // 退出按钮
        document.getElementById('logout-btn').addEventListener('click', async () => {
            await api.logout();
            showToast('已退出登录', 'info');
            renderFavorites();
        });

        batchFetchAllFn = fetchAllFavoritesIds;
        batchFetchPageFn = fetchFavoritesPageIds;
        document.getElementById('select-all-fav-btn').addEventListener('click', selectAll);
        document.getElementById('load-fav-btn').addEventListener('click', () => {
            favoritesState.page = 1;
            loadFavorites();
        });

        document.getElementById('fav-folder').addEventListener('change', (e) => {
            favoritesState.folder_id = e.target.value;
            favoritesState.page = 1;
            loadFavorites();
        });
        document.getElementById('fav-order').addEventListener('change', (e) => {
            favoritesState.order_by = e.target.value;
            favoritesState.page = 1;
            loadFavorites();
        });

        loadFavorites();
    }
}

async function loadFavorites(page = 1) {
    if (page) favoritesState.page = page;

    const contentDiv = document.getElementById('fav-content');
    const paginationDiv = document.getElementById('fav-pagination');

    contentDiv.innerHTML = `<div class="page-loading"><div class="spinner"></div></div>`;
    paginationDiv.innerHTML = '';

    try {
        const data = await api.getFavorites(favoritesState);
        const items = data.items || [];
        favoritesState.page_count = data.page_count || 1;
        favoritesState.total = data.total || 0;

        // 更新收藏夹选择
        const folderSelect = document.getElementById('fav-folder');
        if (folderSelect && data.folder_list && data.folder_list.length > 0) {
            folderSelect.innerHTML = `
                <option value="0">全部收藏</option>
                ${data.folder_list.map(f => `
                    <option value="${escapeHtml(f.folder_id)}" ${f.folder_id === favoritesState.folder_id ? 'selected' : ''}>
                        ${escapeHtml(f.name)}
                    </option>
                `).join('')}
            `;
        }

        if (items.length === 0) {
            contentDiv.innerHTML = `<div class="empty-state">
                <div class="icon">📭</div>
                <p>收藏夹为空</p>
            </div>`;
            return;
        }

        contentDiv.innerHTML = `<div class="comic-grid" id="fav-comic-grid"></div>`;
        const grid = document.getElementById('fav-comic-grid');
        renderComicGrid(grid, items, (id) => {
            // 透传 folder_id 供阅读页随机下一本按"当前所属收藏夹"取范围
            navigateTo(`album/${id}?source=favorites&folder_id=${favoritesState.folder_id}`);
        });

        renderPagination(paginationDiv, favoritesState.page, data.page_count || 1, (p) => {
            favoritesState.page = p;
            loadFavorites(p);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    } catch (e) {
        contentDiv.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>${escapeHtml(e.message)}</p>
            <button class="btn btn-outline" style="margin-top:12px" onclick="loadFavorites()">重试</button>
        </div>`;
    }
}


async function fetchAllFavoritesIds() {
    const allIds = [];
    const totalPages = favoritesState.page_count || 1;
    for (let p = 1; p <= totalPages; p++) {
        try {
            const data = await api.getFavorites({...favoritesState, page: p});
            for (const item of (data.items || [])) {
                allIds.push(item.album_id);
            }
        } catch (e) {}
    }
    return allIds;
}


async function fetchFavoritesPageIds(page) {
    try {
        const data = await api.getFavorites({...favoritesState, page: page});
        return (data.items || []).map(item => item.album_id);
    } catch (e) { return []; }
}
