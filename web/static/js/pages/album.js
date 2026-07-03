/**
 * 本子详情页 — 完整信息、章节列表、下载和观看按钮
 */
async function renderAlbum(albumId) {
    const main = document.getElementById('main-content');

    // 解析 hash 中的 query 参数（如 #album/123?source=favorites&folder_id=0）
    // 透传 source（来源）与 folder_id（收藏夹），供阅读页随机下一本按入口取范围
    const h=window.location.hash; const hq=h.indexOf('?');
    let srcSuffix='';
    if(hq>=0){
        const qp=new URLSearchParams(h.slice(hq));
        const bits=[];
        const s=qp.get('source');    if(s) bits.push('source='+encodeURIComponent(s));
        const f=qp.get('folder_id'); if(f) bits.push('folder_id='+encodeURIComponent(f));
        if(bits.length) srcSuffix='&'+bits.join('&');
    }

    if (!albumId) {
        main.innerHTML = `<div class="empty-state">
            <div class="icon">❓</div>
            <p>请指定本子ID</p>
        </div>`;
        return;
    }

    // 统一打开 reader 入口：先纯本地预检，本地有则转零 API 本地阅读入口
    // 本地命中 → ?dir=zip:<id>&chapter=&chapters= → reader 走本地分支，整链零 JM API
    // 本地未命中 / 预检失败 → 维持原在线 URL（绝不阻断阅读）
    const openReader = async (photoId) => {
        const onlineUrl = '/reader?title=' + albumId + '&volume=' + photoId + srcSuffix;
        try {
            const res = await api.checkLocal(albumId);
            if (res && res.has_local && res.mode === 'zip') {
                const chs = (res.chapters && res.chapters.length) ? res.chapters : ['001'];
                const chap0 = chs[0];
                // 本地阅读入口复用 local.js openLocalChapter 格式（zip 模式）
                window.open('/reader?dir=zip:' + albumId + '&chapter=' + chap0 + '&chapters=' + chs.join(','), '_blank');
                return;
            }
        } catch (e) { /* 预检失败回退在线，不阻断 */ }
        window.open(onlineUrl, '_blank');
    };

    main.innerHTML = `<div class="page-loading"><div class="spinner"></div><p>加载本子详情...</p></div>`;

    try {
        const album = await api.getAlbum(albumId);

        const searchTag = (term, type) => `href="#search?q=${encodeURIComponent(term)}&type=${type}" class="tag-badge tag-clickable"`;
        const tags = (album.tags || []).map(t => `<a ${searchTag(t, 3)} title="搜索标签: ${escapeHtml(t)}">${escapeHtml(t)}</a>`).join('');
        const works = (album.works || []).map(w => `<a ${searchTag(w, 1)} style="background:rgba(68,138,255,0.15);color:#448aff" title="搜索作品: ${escapeHtml(w)}">${escapeHtml(w)}</a>`).join('');
        const actors = (album.actors || []).map(a => `<a ${searchTag(a, 4)} style="background:rgba(255,171,0,0.15);color:#ffab00" title="搜索角色: ${escapeHtml(a)}">${escapeHtml(a)}</a>`).join('');
        const authors = (album.authors || []).map(a => `<a ${searchTag(a, 2)} style="background:rgba(0,200,83,0.15);color:#00c853" title="搜索作者: ${escapeHtml(a)}">${escapeHtml(a)}</a>`).join('') || '未知';
        const episodes = album.episode_list || [];

        main.innerHTML = `
            <div class="page-header">
                <button class="btn btn-outline btn-sm" onclick="window.history.back()">← 返回</button>
            </div>

            <div class="album-detail">
                <!-- 左侧封面 -->
                <div>
                    <div class="album-cover-large" data-cover-id="${escapeHtml(albumId)}">
                        <span style="font-size:4rem;opacity:0.2">📚</span>
                    </div>
                    <div style="margin-top:12px;display:flex;flex-direction:column;gap:8px">
                        <button class="btn btn-primary btn-block" id="view-btn">
                            👀 在线观看
                        </button>
                        <button class="btn btn-primary btn-block" id="download-all-btn">
                            📥 下载全部章节 (共${episodes.length}章)
                        </button>
                        <div class="dropdown" id="export-dropdown">
                            <button class="btn btn-outline btn-block" id="export-options-btn">⚙ 下载选项 ▾</button>
                            <div class="dropdown-content" id="export-menu">
                                <button data-export="zip">📦 导出为 ZIP</button>
                                <button data-export="pdf">📄 导出为 PDF</button>
                                <button data-export="long_img">🖼 导出为长图</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 右侧详情 -->
                <div class="album-info-section">
                    <h1 class="album-title">${escapeHtml(album.name)}</h1>

                    <div class="stats-row">
                        <span class="stat-item">👁 ${escapeHtml(album.views || '0')}</span>
                        <span class="stat-item">❤ ${escapeHtml(album.likes || '0')}</span>
                        <span class="stat-item">💬 ${album.comment_count || 0} 评论</span>
                        <span class="stat-item">📄 ${album.page_count || 0} 页</span>
                    </div>

                    <div class="tags-container">
                        ${tags}
                        ${works}
                        ${actors}
                    </div>

                    <div class="stats-row" style="font-size:0.85rem">
                        <span>✍️ 作者：${authors}</span>
                        <span>📅 发布：${escapeHtml(album.pub_date || '未知')}</span>
                        <span>🔄 更新：${escapeHtml(album.update_date || '未知')}</span>
                    </div>

                    ${album.description ? `
                    <div style="margin-top:8px">
                        <h3 style="font-size:1rem;margin-bottom:8px">📖 简介</h3>
                        <p style="color:var(--text-secondary);font-size:0.9rem;line-height:1.7;white-space:pre-wrap">${escapeHtml(album.description)}</p>
                    </div>` : ''}

                    ${episodes.length > 0 ? `
                    <div style="margin-top:8px">
                        <h3 style="font-size:1rem;margin-bottom:8px">📑 章节列表 (${episodes.length})</h3>
                        <div class="chapter-list" id="chapter-list">
                            ${episodes.map(ep => `
                                <div class="chapter-item" data-photo-id="${escapeHtml(ep.photo_id)}">
                                    <span class="chapter-name">第${escapeHtml(ep.index || '?')}章 · ${escapeHtml(ep.title || '无标题')}</span>
                                    <div class="chapter-actions">
                                        <button class="btn btn-sm btn-outline view-ep-btn" data-id="${escapeHtml(ep.photo_id)}">👀 观看</button>
                                        <button class="btn btn-sm btn-outline download-ep-btn" data-id="${escapeHtml(ep.photo_id)}">📥 下载</button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>` : `<p style="color:var(--text-secondary)">无章节信息</p>`}
                </div>
            </div>
        `;

        // 加载封面图
        loadCoverImages(document.getElementById('main-content'));

        // 在线观看按钮 — 使用 Okuma Reader
        document.getElementById('view-btn').addEventListener('click', () => {
            if (episodes.length > 0) {
                openReader(episodes[0].photo_id);
            } else {
                showToast('没有可观看的章节', 'warning');
            }
        });

        // 下载全部按钮
        document.getElementById('download-all-btn').addEventListener('click', async () => {
            await startDownload(albumId, 'album');
        });

        // 导出选项下拉菜单
        const exportBtn = document.getElementById('export-options-btn');
        const exportMenu = document.getElementById('export-menu');
        exportBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            exportMenu.classList.toggle('show');
        });
        document.addEventListener('click', () => exportMenu.classList.remove('show'));

        // 导出选项
        exportMenu.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const exportType = btn.dataset.export;
                exportMenu.classList.remove('show');
                await startDownload(albumId, 'album', {
                    export_zip: exportType === 'zip',
                    export_pdf: exportType === 'pdf',
                    export_long_img: exportType === 'long_img',
                });
            });
        });

        // 单个章节观看 — Okuma Reader
        document.querySelectorAll('.view-ep-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                openReader(btn.dataset.id);
            });
        });

        // 单个章节下载
        document.querySelectorAll('.download-ep-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await startDownload(btn.dataset.id, 'photo');
            });
        });

        // 点击章节行 → Okuma Reader
        document.querySelectorAll('.chapter-item').forEach(item => {
            item.addEventListener('click', () => {
                openReader(item.dataset.photoId);
            });
        });

    } catch (e) {
        main.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>${escapeHtml(e.message)}</p>
            <button class="btn btn-outline" style="margin-top:12px" onclick="window.history.back()">返回</button>
        </div>`;
    }
}

/**
 * 打开在线观看器 — 专业漫画阅读体验
 * 已改用独立 Okuma /reader 页面
 */

// ---- 旧 viewer 已移除，请使用 /reader 页面 ----

function _removed_openViewer() {}

async function startDownload(jmId, type, extras = {}) {
    try {
        let result;
        if (type === 'album') {
            result = await api.startAlbumDownload(jmId, extras);
        } else {
            result = await api.startPhotoDownload(jmId, extras);
        }
        showToast(`下载已开始 (JM${jmId})，前往「下载管理」查看进度`, 'success', 5000);
        updateDownloadBadge();
    } catch (e) {
        showToast(e.message, 'error');
    }
}
