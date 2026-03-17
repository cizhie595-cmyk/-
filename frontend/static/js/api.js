/**
 * Amazon Visionary Sourcing Tool - API 客户端
 * 封装所有后端 API 调用
 */

const API_BASE = '/api/v1';

class APIClient {
    constructor() {
        this.token = localStorage.getItem('auth_token');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('auth_token');
    }

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

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }

            return result;
        } catch (error) {
            console.error(`API Error [${method} ${path}]:`, error);
            throw error;
        }
    }

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

    // ---- Auth ----
    async login(email, password) {
        const result = await this.request('POST', '/auth/login', { email, password });
        if (result && result.token) {
            this.setToken(result.token);
        }
        return result;
    }

    async register(data) {
        return await this.request('POST', '/auth/register', data);
    }

    async getProfile() {
        return await this.request('GET', '/auth/profile');
    }

    async getQuota() {
        return await this.request('GET', '/auth/quota');
    }

    // ---- Projects ----
    async createProject(data) {
        return await this.request('POST', '/projects', data);
    }

    async getProjects() {
        return await this.request('GET', '/projects');
    }

    async getProject(id) {
        return await this.request('GET', `/projects/${id}`);
    }

    async startScraping(projectId) {
        return await this.request('POST', `/projects/${projectId}/scrape`);
    }

    async getProducts(projectId, params = {}) {
        const query = new URLSearchParams(params).toString();
        return await this.request('GET', `/projects/${projectId}/products?${query}`);
    }

    async filterProducts(projectId, rules) {
        return await this.request('POST', `/projects/${projectId}/filter`, { rules });
    }

    // ---- Analysis ----
    async startVisualAnalysis(asin) {
        return await this.request('POST', '/analysis/visual', { asin });
    }

    async startReviewAnalysis(asin) {
        return await this.request('POST', '/analysis/reviews', { asin });
    }

    async getAnalysisResult(taskId) {
        return await this.request('GET', `/analysis/result/${taskId}`);
    }

    async generateReport(projectId) {
        return await this.request('POST', `/analysis/report/${projectId}`);
    }

    // ---- 3D ----
    async generate3D(imageUrl, options = {}) {
        return await this.request('POST', '/3d/generate', { image_url: imageUrl, ...options });
    }

    async get3DStatus(taskId) {
        return await this.request('GET', `/3d/status/${taskId}`);
    }

    async render3DVideo(assetId, options = {}) {
        return await this.request('POST', `/3d/render/${assetId}/video`, options);
    }

    // ---- Profit ----
    async calculateProfit(params) {
        return await this.request('POST', '/profit/calculate', params);
    }

    async searchSource(imageUrl) {
        return await this.request('POST', '/profit/image-search', { image_url: imageUrl });
    }

    // ---- Upload ----
    async uploadDataFile(file) {
        return await this.uploadFile('/upload/parse', file);
    }

    async confirmMapping(fileId, mapping) {
        return await this.request('POST', '/upload/confirm-mapping', {
            file_id: fileId,
            column_mapping: mapping,
        });
    }

    // ---- Trends ----
    async getGoogleTrends(keywords, marketplace = 'US') {
        return await this.request('POST', '/upload/trends', { keywords, marketplace });
    }

    // ---- Subscription ----
    async getSubscription() {
        return await this.request('GET', '/monetization/subscription');
    }

    async upgradePlan(planId) {
        return await this.request('POST', '/monetization/subscribe', { plan_id: planId });
    }
}

// 全局实例
const api = new APIClient();

// ---- 工具函数 ----

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
    }).format(amount);
}

function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
    });
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; z-index: 9999;
        padding: 12px 24px; border-radius: 8px; color: white;
        font-size: 0.9rem; animation: slideIn 0.3s ease;
        background: ${type === 'success' ? '#22c55e' : type === 'danger' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#6366f1'};
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}
