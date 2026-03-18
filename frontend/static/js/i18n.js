/**
 * Coupang 选品系统 - 前端国际化 (i18n) 模块
 * 支持: zh_CN / en_US / ko_KR 动态切换
 */

class I18nManager {
    constructor() {
        this.currentLang = localStorage.getItem('app_language') || 'en_US';
        this.translations = {};
        this.loaded = false;
    }

    /**
     * 初始化: 加载语言包
     */
    async init() {
        await this.loadLanguage(this.currentLang);
        this.applyTranslations();
        this.renderLanguageSwitcher();
        this.loaded = true;
    }

    /**
     * 加载指定语言包
     */
    async loadLanguage(lang) {
        try {
            const response = await fetch(`/api/i18n/${lang}`);
            if (response.ok) {
                this.translations = await response.json();
                this.currentLang = lang;
                localStorage.setItem('app_language', lang);
            } else {
                console.warn(`[i18n] Failed to load language: ${lang}`);
            }
        } catch (err) {
            console.error(`[i18n] Error loading language:`, err);
        }
    }

    /**
     * 翻译键值
     * @param {string} key - 翻译键 (如 "nav.dashboard")
     * @param {object} params - 插值参数
     * @returns {string}
     */
    t(key, params = {}) {
        const parts = key.split('.');
        let value = this.translations;

        for (const part of parts) {
            if (value && typeof value === 'object') {
                value = value[part];
            } else {
                return `[${key}]`;
            }
        }

        if (typeof value !== 'string') return `[${key}]`;

        // 插值替换: {count} -> params.count
        return value.replace(/\{(\w+)\}/g, (match, name) => {
            return params[name] !== undefined ? params[name] : match;
        });
    }

    /**
     * 切换语言
     */
    async switchLanguage(lang) {
        if (lang === this.currentLang) return;
        await this.loadLanguage(lang);
        this.applyTranslations();
        this.updateSwitcherUI();

        // 通知后端保存偏好
        try {
            await fetch('/api/i18n/preference', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language: lang }),
            });
        } catch (e) {
            // 忽略
        }
    }

    /**
     * 自动翻译页面中带 data-i18n 属性的元素
     */
    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translated = this.t(key);
            if (translated && !translated.startsWith('[')) {
                // 根据元素类型设置文本
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    el.placeholder = translated;
                } else if (el.hasAttribute('data-i18n-attr')) {
                    el.setAttribute(el.getAttribute('data-i18n-attr'), translated);
                } else {
                    el.textContent = translated;
                }
            }
        });

        // 更新 <html lang>
        const langMap = { 'zh_CN': 'zh', 'en_US': 'en', 'ko_KR': 'ko' };
        document.documentElement.lang = langMap[this.currentLang] || 'en';
    }

    /**
     * 渲染语言切换器
     */
    renderLanguageSwitcher() {
        const container = document.getElementById('language-switcher');
        if (!container) return;

        const languages = [
            { code: 'zh_CN', label: '中文', flag: '🇨🇳' },
            { code: 'en_US', label: 'EN', flag: '🇺🇸' },
            { code: 'ko_KR', label: '한국어', flag: '🇰🇷' },
        ];

        container.innerHTML = `
            <div class="lang-switcher">
                ${languages.map(lang => `
                    <button class="lang-btn ${lang.code === this.currentLang ? 'active' : ''}"
                            data-lang="${lang.code}"
                            title="${lang.label}">
                        <span class="lang-flag">${lang.flag}</span>
                        <span class="lang-label">${lang.label}</span>
                    </button>
                `).join('')}
            </div>
        `;

        // 绑定事件
        container.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchLanguage(btn.dataset.lang);
            });
        });
    }

    /**
     * 更新切换器 UI 状态
     */
    updateSwitcherUI() {
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === this.currentLang);
        });
    }
}

// 全局实例
const i18n = new I18nManager();

// 页面加载后初始化
document.addEventListener('DOMContentLoaded', () => {
    i18n.init();
});

// 全局翻译函数
function t(key, params) {
    return i18n.t(key, params);
}
