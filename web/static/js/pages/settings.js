/**
 * 设置页面 — 下载目录、代理、并发、图片格式
 */
async function renderSettings() {
    const main = document.getElementById('main-content');

    main.innerHTML = `<div class="page-loading"><div class="spinner"></div><p>加载设置...</p></div>`;

    let settings;
    try {
        settings = await api.getSettings();
    } catch (e) {
        main.innerHTML = `<div class="empty-state">
            <div class="icon">❌</div>
            <p>加载设置失败: ${escapeHtml(e.message)}</p>
        </div>`;
        return;
    }

    main.innerHTML = `
        <div class="page-header">
            <h1>⚙ 设置</h1>
            <p>配置下载参数，设置会自动保存</p>
        </div>

        <div class="settings-form">
            <!-- 账号设置 -->
            <div class="settings-section">
                <h3>🔑 账号设置（保存后启动时自动登录）</h3>
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" id="setting-username" value="${escapeHtml(settings.jm_username || '')}" autocomplete="username">
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input type="password" id="setting-password" value="${escapeHtml(settings.jm_password || '')}" autocomplete="current-password">
                </div>
            </div>

            <!-- 基本设置 -->
            <div class="settings-section">
                <h3>📁 基本设置</h3>
                <div class="form-group">
                    <label>下载目录</label>
                    <input type="text" id="setting-download-dir" value="${escapeHtml(settings.download_dir || '')}">
                    <div class="hint">下载的本子将保存在此目录</div>
                </div>
                <div class="form-group">
                    <label>图片格式</label>
                    <select id="setting-image-suffix">
                        <option value="">保持原格式</option>
                        <option value=".jpg" ${settings.image_suffix === '.jpg' ? 'selected' : ''}>JPG</option>
                        <option value=".png" ${settings.image_suffix === '.png' ? 'selected' : ''}>PNG</option>
                        <option value=".webp" ${settings.image_suffix === '.webp' ? 'selected' : ''}>WebP</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>客户端类型</label>
                    <select id="setting-client-impl">
                        <option value="api" ${settings.client_impl === 'api' ? 'selected' : ''}>API (移动端，推荐)</option>
                        <option value="html" ${settings.client_impl === 'html' ? 'selected' : ''}>HTML (网页端)</option>
                    </select>
                    <div class="hint">API模式不限制IP，HTML模式效率更高但可能限制地区</div>
                </div>
            </div>

            <!-- 网络设置 -->
            <div class="settings-section">
                <h3>🌐 网络设置</h3>
                <div class="form-group">
                    <label>代理地址</label>
                    <input type="text" id="setting-proxy" value="${escapeHtml(settings.proxy || '')}">
                    <div class="hint">例如 http://127.0.0.1:7890（Clash默认端口）</div>
                </div>
                <button class="btn btn-outline btn-sm" id="test-proxy-btn">🔍 测试代理</button>
                <span id="proxy-test-result" style="margin-left:12px;font-size:0.85rem"></span>
                <div class="form-group" style="margin-top:16px">
                    <label>重试次数</label>
                    <input type="number" id="setting-retry-times" value="${settings.retry_times || 5}" min="1" max="20">
                </div>
            </div>

            <!-- 下载设置 -->
            <div class="settings-section">
                <h3>📥 下载设置</h3>
                <div class="form-group">
                    <label>最多同时下载任务数</label>
                    <input type="number" id="setting-max-parallel" value="${settings.max_parallel_downloads || 3}" min="1" max="20">
                    <div class="hint">批量下载时最多同时跑几个，其余排队。建议 2-5，避免被封</div>
                </div>
                <div class="form-group">
                    <label>图片并发数</label>
                    <input type="number" id="setting-thread-image" value="${settings.thread_count_image || 30}" min="1" max="50">
                    <div class="hint">同时下载的图片数量，建议 10-30</div>
                </div>
                <div class="form-group">
                    <label>章节并发数</label>
                    <input type="number" id="setting-thread-photo" value="${settings.thread_count_photo || 5}" min="1" max="10">
                    <div class="hint">同时下载的章节数量，建议 3-8</div>
                </div>
            </div>

            <!-- 压缩设置 -->
            <div class="settings-section">
                <h3>📦 压缩设置</h3>
                <div class="form-group">
                    <label>下载后自动压缩为 ZIP</label>
                    <select id="setting-zip-enabled">
                        <option value="true" ${settings.zip_enabled !== false ? 'selected' : ''}>启用（下载后自动打包为 .zip）</option>
                        <option value="false" ${settings.zip_enabled === false ? 'selected' : ''}>禁用（保留图片文件夹）</option>
                    </select>
                    <div class="hint">压缩包解压后直接是图片，无子文件夹</div>
                </div>
                <div class="form-group">
                    <label>压缩后删除原始图片</label>
                    <select id="setting-zip-delete">
                        <option value="false" ${!settings.zip_delete_after ? 'selected' : ''}>保留图片</option>
                        <option value="true" ${settings.zip_delete_after ? 'selected' : ''}>删除图片（仅保留 .zip）</option>
                    </select>
                </div>
            </div>

            <button class="btn btn-primary" id="save-settings-btn">💾 保存设置</button>
        </div>
    `;

    // 保存按钮
    document.getElementById('save-settings-btn').addEventListener('click', async () => {
        const newSettings = {
            download_dir: document.getElementById('setting-download-dir').value.trim(),
            image_suffix: document.getElementById('setting-image-suffix').value,
            client_impl: document.getElementById('setting-client-impl').value,
            proxy: document.getElementById('setting-proxy').value.trim(),
            retry_times: parseInt(document.getElementById('setting-retry-times').value) || 5,
            thread_count_image: parseInt(document.getElementById('setting-thread-image').value) || 30,
            thread_count_photo: parseInt(document.getElementById('setting-thread-photo').value) || 5,
            zip_enabled: document.getElementById('setting-zip-enabled').value === 'true',
            zip_delete_after: document.getElementById('setting-zip-delete').value === 'true',
            max_parallel_downloads: parseInt(document.getElementById('setting-max-parallel').value) || 3,
            jm_username: document.getElementById('setting-username').value.trim(),
            jm_password: document.getElementById('setting-password').value.trim(),
        };

        try {
            await api.updateSettings(newSettings);
            showToast('设置已保存 ✓', 'success');
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 测试代理按钮
    document.getElementById('test-proxy-btn').addEventListener('click', async () => {
        const proxy = document.getElementById('setting-proxy').value.trim();
        const resultEl = document.getElementById('proxy-test-result');

        resultEl.textContent = '测试中...';
        resultEl.style.color = 'var(--text-secondary)';

        try {
            const result = await api.testProxy(proxy);
            if (result.jm_accessible || result.google_accessible) {
                resultEl.textContent = '✓ ' + result.message;
                resultEl.style.color = 'var(--success)';
            } else {
                resultEl.textContent = '✗ ' + result.message;
                resultEl.style.color = 'var(--error)';
            }
        } catch (e) {
            resultEl.textContent = '✗ 测试失败';
            resultEl.style.color = 'var(--error)';
        }
    });
}
