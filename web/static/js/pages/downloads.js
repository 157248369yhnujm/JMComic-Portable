/**
 * 下载管理页面 — 实时进度、取消、历史
 */
let downloadPollTimer = null;

async function renderDownloads() {
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="page-header">
            <h1>📥 下载管理</h1>
            <p>管理所有下载任务 — 查看进度、取消任务、浏览历史</p>
        </div>

        <div style="margin-bottom:16px;display:flex;gap:8px">
            <button class="btn btn-outline btn-sm" id="refresh-dl-btn">🔄 刷新</button>
            <button class="btn btn-outline btn-sm" id="clear-dl-btn">🗑 清除历史</button>
        </div>

        <div id="download-content">
            <div class="page-loading"><div class="spinner"></div></div>
        </div>
    `;

    document.getElementById('refresh-dl-btn').addEventListener('click', loadDownloads);
    document.getElementById('clear-dl-btn').addEventListener('click', async () => {
        if (!confirm('确定要清除所有已完成的下载记录吗？')) return;
        try {
            const result = await api.clearHistory();
            showToast(`已清除 ${result.cleared} 条记录`, 'success');
            loadDownloads();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    loadDownloads();

    // 开始轮询（如果有活跃任务）
    startPolling();
}

function startPolling() {
    if (downloadPollTimer) clearInterval(downloadPollTimer);
    downloadPollTimer = setInterval(async () => {
        try {
            const data = await api.listDownloads();
            const hasActive = data.tasks.some(t => t.status === 'pending' || t.status === 'running');
            if (!hasActive) {
                // 没有活跃任务时降低轮询频率
                clearInterval(downloadPollTimer);
                downloadPollTimer = setInterval(() => loadDownloads(), 10000);
            }
            loadDownloads();
        } catch (e) {
            // 静默失败
        }
    }, 1000);
}

async function loadDownloads() {
    const container = document.getElementById('download-content');
    if (!container) return;

    try {
        const data = await api.listDownloads();
        const tasks = data.tasks || [];

        if (tasks.length === 0) {
            container.innerHTML = `<div class="empty-state">
                <div class="icon">📭</div>
                <p>暂无下载任务</p>
                <p style="font-size:0.8rem;color:var(--text-muted)">在首页或搜索中找到本子，点击下载即可开始</p>
            </div>`;
            return;
        }

        container.innerHTML = `
            <div style="margin-bottom:12px;font-size:0.85rem;color:var(--text-secondary)">
                活跃任务: ${data.active_count || 0} | 总计: ${tasks.length}
            </div>
            <div class="download-list">
                ${tasks.map(t => renderTaskItem(t)).join('')}
            </div>
        `;

        // 绑定取消按钮
        container.querySelectorAll('.cancel-task-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                try {
                    await api.cancelDownload(btn.dataset.taskId);
                    showToast('已发送取消信号', 'info');
                    loadDownloads();
                } catch (e) {
                    showToast(e.message, 'error');
                }
            });
        });

        updateDownloadBadge();
    } catch (e) {
        container.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>加载失败: ${escapeHtml(e.message)}</p>
        </div>`;
    }
}

function renderTaskItem(t) {
    const statusLabels = {
        pending: '⏳ 等待中',
        queued: '📋 排队中',
        running: '🔄 下载中',
        completed: '✅ 已完成',
        failed: '❌ 失败',
        cancelled: '⚠️ 已取消',
    };

    const typeLabel = t.type === 'album' ? '本子' : '章节';
    const statusClass = `status-${t.status}`;
    const progress = t.progress || {};
    const elapsed = t.elapsed ? `${t.elapsed}秒` : '';
    const canCancel = t.status === 'pending' || t.status === 'queued' || t.status === 'running';
    const hasProgress = t.status === 'running' && (progress.total_photos > 0 || progress.total_images > 0);

    let progressHtml = '';
    if (hasProgress || t.status === 'running') {
        const pct = progress.percentage || 0;
        let detailText = '';
        if (progress.total_photos > 0) {
            detailText = `章节 ${progress.current_photo}/${progress.total_photos}`;
            if (progress.total_images > 0) {
                detailText += ` · 图片 ${progress.current_image}/${progress.total_images}`;
            }
        }
        const mbInfo = [];
        if (progress.downloaded_mb > 0) {
            mbInfo.push(`📦 ${progress.downloaded_mb.toFixed(1)} MB`);
        }
        if (progress.total_mb > 0) {
            mbInfo.push(`预估 ${progress.total_mb.toFixed(1)} MB`);
        }
        if (progress.download_speed) {
            mbInfo.push(`⚡ ${progress.download_speed}`);
        }

        progressHtml = `
            <div class="progress-bar">
                <div class="progress-fill" style="width:${pct}%"></div>
            </div>
            <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:2px">
                ${detailText} (${pct.toFixed(1)}%)
                ${progress.current_photo_name ? ' · ' + escapeHtml(progress.current_photo_name) : ''}
                ${mbInfo.length > 0 ? ' · ' + mbInfo.join(' · ') : ''}
            </div>
        `;
    }

    return `
    <div class="download-item">
        <div class="task-info">
            <div class="task-title">
                <span class="${statusClass}">${statusLabels[t.status] || t.status}</span>
                ${typeLabel} · JM${escapeHtml(t.jm_id)}
                ${progress.album_title ? ' · ' + escapeHtml(progress.album_title) : ''}
            </div>
            ${progressHtml}
            <div class="task-detail">
                ${t.save_path ? `📁 ${escapeHtml(t.save_path)}` : ''}
                ${elapsed ? ` · ⏱ ${elapsed}` : ''}
                ${t.error ? `<span style="color:var(--error)"> · ${escapeHtml(t.error)}</span>` : ''}
            </div>
        </div>
        <div class="task-actions">
            ${canCancel ? `<button class="btn btn-danger btn-sm cancel-task-btn" data-task-id="${t.task_id}">取消</button>` : ''}
        </div>
    </div>`;
}
