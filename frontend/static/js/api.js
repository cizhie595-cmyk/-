/**
 * Amazon Visionary Sourcing Tool - API 客户端
 * 封装所有后端 API 调用，包含额度校验拦截 (PRD 2.3)
 */

const API_BASE = '/api';

class APIClient {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this._quotaCache = null;
        this._quotaCacheTime = 0;
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('auth_token');
        this._quotaCache = null;
    }

    /**
     * 通用请求方法
     * @param {string} method - HTTP 方法
     * @param {string} path - API 路径 (相对于 /api)
     * @param {object} data - 请求体
     * @param {object} options - 额外 fetch 选项
     */
    async request(method, path, data = null, options = {}) {
        const url = `${API_BASE}${path}`;
        const headers = { 'Content-Type': 'application/json' };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const config = { method, headers, ...options };

        if (data && method !== 'GET') {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, config);

            if (response.status === 401) {
                this.clearToken();
                window.location.href = '/auth/login';
                return null;
            }

            // 解析限流响应头并缓存
            const rateLimitRemaining = response.headers.get('X-RateLimit-Remaining');
            const rateLimitLimit = response.headers.get('X-RateLimit-Limit');
            const rateLimitReset = response.headers.get('X-RateLimit-Reset');
            if (rateLimitRemaining !== null) {
                this._rateLimit = {
                    remaining: parseInt(rateLimitRemaining),
                    limit: parseInt(rateLimitLimit) || 100,
                    reset: parseInt(rateLimitReset) || 0,
                };
                // 当剩余请求数低于 20% 时显示警告
                if (this._rateLimit.remaining > 0 && this._rateLimit.remaining <= this._rateLimit.limit * 0.2) {
                    this._showRateLimitWarning(this._rateLimit.remaining, this._rateLimit.limit);
                }
            }

            // 处理限流/额度不足响应
            if (response.status === 429) {
                const result = await response.json();
                const retryAfter = response.headers.get('Retry-After') || result.retry_after || '60';
                if (result.error === 'quota_exceeded') {
                    showToast(`额度不足: ${result.message || '请升级订阅'}`, 'warning');
                } else {
                    showToast(`请求过于频繁，请 ${retryAfter} 秒后重试`, 'warning');
                }
                return null;
            }

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || result.message || `HTTP ${response.status}`);
            }

            return result;
        } catch (error) {
            console.error(`API Error [${method} ${path}]:`, error);
            throw error;
        }
    }

    /**
     * 文件上传
     */
    async uploadFile(path, file, extraFields = {}) {
        const url = `${API_BASE}${path}`;
        const formData = new FormData();
        formData.append('file', file);

        for (const [key, value] of Object.entries(extraFields)) {
            formData.append(key, value);
        }

        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: formData,
        });

        return await response.json();
    }

    // ================================================================
    // 额度校验拦截 (PRD 2.3)
    // ================================================================

    /**
     * 获取当前用户额度（带缓存，5分钟刷新）
     */
    async getQuotaCached() {
        const now = Date.now();
        if (this._quotaCache && (now - this._quotaCacheTime) < 300000) {
            return this._quotaCache;
        }
        try {
            const result = await this.request('GET', '/v1/user/quota');
            if (result && result.success) {
                this._quotaCache = result;
                this._quotaCacheTime = now;
            }
            return result;
        } catch (e) {
            return null;
        }
    }

    /**
     * 前端额度校验拦截
     * 在执行消耗额度的操作前调用，若额度不足则弹出提示并返回 false
     * @param {string} quotaType - 额度类型: scrape, analysis, 3d_generate, render_video
     * @param {number} count - 需要消耗的数量 (默认 1)
     * @returns {boolean} - true 表示额度充足可以继续，false 表示额度不足
     */
    async checkQuota(quotaType, count = 1) {
        try {
            const quota = await this.getQuotaCached();
            if (!quota || !quota.quotas) return true; // 获取失败时不阻止操作

            const detail = quota.quotas[quotaType];
            if (!detail) return true;

            if (detail.remaining < count) {
                const typeNames = {
                    scrape: '数据抓取',
                    analysis: '深度分析',
                    '3d_generate': '3D 生成',
                    render_video: '视频渲染',
                };
                const name = typeNames[quotaType] || quotaType;
                showToast(`${name}额度不足 (剩余 ${detail.remaining}/${detail.limit})，请升级订阅`, 'warning');
                return false;
            }
            return true;
        } catch (e) {
            return true; // 出错时不阻止
        }
    }

    /**
     * 刷新额度缓存
     */
    invalidateQuotaCache() {
        this._quotaCache = null;
        this._quotaCacheTime = 0;
    }

    // ================================================================
    // Auth API
    // ================================================================

    async login(loginId, password) {
        const result = await this.request('POST', '/auth/login', { login_id: loginId, password });
        // 后端返回 {success, data: {access_token, refresh_token, ...}}
        if (result && result.data && result.data.access_token) {
            this.setToken(result.data.access_token);
            // 保存 refresh_token
            if (result.data.refresh_token) {
                localStorage.setItem('refresh_token', result.data.refresh_token);
            }
        } else if (result && result.token) {
            // 兼容旧格式
            this.setToken(result.token);
        }
        return result;
    }

    async register(data) {
        return await this.request('POST', '/auth/register', data);
    }

    async getProfile() {
        return await this.request('GET', '/auth/me');
    }

    async getQuota() {
        return await this.request('GET', '/v1/user/quota');
    }

    // ================================================================
    // Projects API (PRD 8.3)
    // ================================================================

    async createProject(data) {
        return await this.request('POST', '/v1/projects/create', data);
    }

    async getProjects(params = {}) {
        const query = new URLSearchParams(params).toString();
        const path = query ? `/v1/projects?${query}` : '/v1/projects';
        return await this.request('GET', path);
    }

    async getProject(id) {
        return await this.request('GET', `/v1/projects/${id}`);
    }

    async startScraping(projectId, scrapeDepth = 100) {
        // 额度校验
        if (!(await this.checkQuota('scrape'))) return null;
        const result = await this.request('POST', `/v1/projects/${projectId}/scrape`, { scrape_depth: scrapeDepth });
        this.invalidateQuotaCache();
        return result;
    }

    async getProducts(projectId, params = {}) {
        const query = new URLSearchParams(params).toString();
        return await this.request('GET', `/v1/projects/${projectId}/products?${query}`);
    }

    async filterProducts(projectId, rules) {
        return await this.request('POST', `/v1/projects/${projectId}/filter/rules`, { rules });
    }

    async aiFilter(projectId, description) {
        if (!(await this.checkQuota('analysis'))) return null;
        return await this.request('POST', `/v1/projects/${projectId}/filter/ai`, { user_description: description });
    }

    // ================================================================
    // Analysis API (PRD 8.4)
    // ================================================================

    async startVisualAnalysis(asin, dimensions = []) {
        if (!(await this.checkQuota('analysis'))) return null;
        const result = await this.request('POST', '/v1/analysis/visual', { asin, dimensions });
        this.invalidateQuotaCache();
        return result;
    }

    async startReviewAnalysis(asin, reviewCount = 500) {
        if (!(await this.checkQuota('analysis'))) return null;
        const result = await this.request('POST', '/v1/analysis/reviews', { asin, review_count: reviewCount });
        this.invalidateQuotaCache();
        return result;
    }

    async getAnalysisResult(taskId) {
        return await this.request('GET', `/v1/analysis/${taskId}/result`);
    }

    async generateReport(projectId) {
        return await this.request('POST', '/v1/analysis/report/generate', { project_id: projectId });
    }

    // ================================================================
    // 3D API (PRD 8.5)
    // ================================================================

    async generate3D(imageUrls, options = {}) {
        if (!(await this.checkQuota('3d_generate'))) return null;
        const result = await this.request('POST', '/v1/3d/generate', { image_urls: imageUrls, ...options });
        this.invalidateQuotaCache();
        return result;
    }

    async get3DStatus(assetId) {
        return await this.request('GET', `/v1/3d/${assetId}/status`);
    }

    async render3DVideo(assetId, options = {}) {
        if (!(await this.checkQuota('render_video'))) return null;
        const result = await this.request('POST', `/v1/3d/${assetId}/render-video`, options);
        this.invalidateQuotaCache();
        return result;
    }

    async get3DVideo(assetId) {
        return await this.request('GET', `/v1/3d/${assetId}/video`);
    }

    async get3DAssets() {
        return await this.request('GET', '/v1/3d/assets');
    }

    // ================================================================
    // Profit & Supply Chain API (PRD 8.6)
    // ================================================================

    async calculateProfit(params) {
        return await this.request('POST', '/v1/profit/calculate', params);
    }

    async batchCalculateProfit(items) {
        return await this.request('POST', '/v1/profit/batch', { products: items });
    }

    async imageSearch(imageUrl) {
        return await this.request('POST', '/v1/supply/image-search', { image_url: imageUrl });
    }

    async keywordSearch(keyword) {
        return await this.request('POST', '/v1/supply/keyword-search', { keyword });
    }

    // ================================================================
    // Upload & Trends API
    // ================================================================

    async uploadDataFile(file) {
        return await this.uploadFile('/v1/upload/parse', file);
    }

    async confirmMapping(fileId, mapping) {
        return await this.request('POST', '/v1/upload/confirm-mapping', {
            file_id: fileId,
            column_mapping: mapping,
        });
    }

    async getGoogleTrends(keywords, marketplace = 'US') {
        return await this.request('POST', '/v1/upload/trends', { keywords, marketplace });
    }

    // ================================================================
    // Asset Download API (PRD 3.3.1)
    // ================================================================

    /**
     * 下载单品素材 ZIP 包
     */
    downloadProductAssets(asin, include3d = false, includeVideo = false) {
        const params = new URLSearchParams();
        if (include3d) params.set('include_3d', 'true');
        if (includeVideo) params.set('include_video', 'true');
        const url = `/api/v1/assets/download/${asin}?${params.toString()}`;
        window.open(url, '_blank');
    }

    /**
     * 下载项目级素材 ZIP 包
     */
    downloadProjectAssets(projectId, maxProducts = 50) {
        const url = `/api/v1/assets/download/project/${projectId}?max_products=${maxProducts}`;
        window.open(url, '_blank');
    }

    // ================================================================
    // Subscription & Monetization API
    // ================================================================

    async getSubscriptionPlans() {
        return await this.request('GET', '/subscription/plans');
    }

    async getMySubscription() {
        return await this.request('GET', '/subscription/me');
    }

    async upgradePlan(planId) {
        return await this.request('POST', '/subscription/upgrade', { plan_id: planId });
    }

    async cancelSubscription() {
        return await this.request('POST', '/subscription/cancel');
    }

    async getUsageStats() {
        return await this.request('GET', '/subscription/usage');
    }

    // ================================================================
    // API Keys & Settings
    // ================================================================

    async getApiKeyServices() {
        return await this.request('GET', '/keys/services');
    }

    async getAllApiKeys() {
        return await this.request('GET', '/keys/all');
    }

    async saveApiKey(serviceId, config) {
        return await this.request('POST', `/keys/${serviceId}`, config);
    }

    async testApiKey(serviceId) {
        return await this.request('POST', `/keys/${serviceId}/test`);
    }

    // ================================================================
    // Affiliate
    // ================================================================

    async generateAffiliateLink(url, marketplace) {
        return await this.request('POST', '/affiliate/link', { url, marketplace });
    }

    async batchAffiliateLinks(urls, marketplace) {
        return await this.request('POST', '/affiliate/batch', { urls, marketplace });
    }

    // ================================================================
    // Rate Limit Info
    // ================================================================

    /**
     * 获取当前限流状态
     * @returns {{remaining: number, limit: number, reset: number}|null}
     */
    getRateLimit() {
        return this._rateLimit || null;
    }

    /**
     * 显示限流警告（每 60 秒最多显示一次）
     */
    _showRateLimitWarning(remaining, limit) {
        const now = Date.now();
        if (this._lastRateLimitWarning && (now - this._lastRateLimitWarning) < 60000) {
            return; // 防止频繁显示
        }
        this._lastRateLimitWarning = now;
        showToast(`API 请求即将达到限制（剩余 ${remaining}/${limit}）`, 'warning');
    }

    // ================================================================
    // Notifications API
    // ================================================================

    async getNotifications(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await this.request('GET', `/notifications?${query}`);
    }

    async markNotificationRead(id) {
        return await this.request('PUT', `/notifications/${id}/read`);
    }

    async markAllNotificationsRead() {
        return await this.request('PUT', '/notifications/read-all');
    }

    async getNotificationPreferences() {
        return await this.request('GET', '/notifications/preferences');
    }

    async updateNotificationPreferences(prefs) {
        return await this.request('PUT', '/notifications/preferences', prefs);
    }

    // ================================================================
    // Team API
    // ================================================================

    async getTeamMembers() {
        return await this.request('GET', '/team/members');
    }

    async inviteTeamMember(data) {
        return await this.request('POST', '/team/invite', data);
    }

    async updateMemberRole(memberId, role) {
        return await this.request('PUT', `/team/members/${memberId}`, { role });
    }

    async removeTeamMember(memberId) {
        return await this.request('DELETE', `/team/members/${memberId}`);
    }

    async getTeamActivity(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await this.request('GET', `/team/activity?${query}`);
    }

    // ================================================================
    // Export API
    // ================================================================

    async exportProjectData(projectId, format = 'csv') {
        return await this.request('GET', `/v1/export/project/${projectId}?format=${format}`);
    }

    async exportReport(projectId, format = 'pdf') {
        return await this.request('GET', `/v1/export/report/${projectId}?format=${format}`);
    }
}

// 全局实例
const api = new APIClient();


// ================================================================
// 工具函数
// ================================================================

function formatNumber(num) {
    if (num == null) return '-';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatCurrency(amount, currency = 'USD') {
    if (amount == null) return '-';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
    }).format(amount);
}

function formatPercent(value) {
    if (value == null) return '-';
    return (value * 100).toFixed(1) + '%';
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
    });
}

/**
 * Toast 通知 (使用 base.html 中的 toast-container)
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (container) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.classList.add('toast-show'), 10);
        setTimeout(() => {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    } else {
        // Fallback: 独立 toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            padding: 12px 24px; border-radius: 8px; color: white;
            font-size: 0.9rem; animation: slideIn 0.3s ease;
            background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#6366f1'};
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }
}

/**
 * 按钮加载状态管理 (PRD 2.2 - 防重复点击)
 */
function setButtonLoading(btn, loading = true) {
    if (loading) {
        btn.classList.add('btn-loading');
        btn.disabled = true;
        btn._originalText = btn.textContent;
    } else {
        btn.classList.remove('btn-loading');
        btn.disabled = false;
        if (btn._originalText) {
            btn.textContent = btn._originalText;
        }
    }
}

/**
 * 防抖
 */
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

/**
 * 生成骨架屏 HTML
 */
function createSkeleton(type = 'card', count = 3) {
    let html = '';
    for (let i = 0; i < count; i++) {
        if (type === 'card') {
            html += '<div class="skeleton skeleton-card"></div>';
        } else if (type === 'text') {
            html += `
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text medium"></div>
                <div class="skeleton skeleton-text short"></div>
            `;
        } else if (type === 'table-row') {
            html += `<tr>
                <td><div class="skeleton skeleton-text" style="width:60%"></div></td>
                <td><div class="skeleton skeleton-text" style="width:40%"></div></td>
                <td><div class="skeleton skeleton-text" style="width:50%"></div></td>
                <td><div class="skeleton skeleton-text" style="width:30%"></div></td>
            </tr>`;
        }
    }
    return html;
}
