/**
 * Amazon Visionary Sourcing Tool - Skeleton Loader (PRD 2.2)
 *
 * Global skeleton screen loading system:
 * - Auto-generates skeleton placeholders matching page layout
 * - Smooth fade transition from skeleton to real content
 * - Prevents layout shift (CLS) during loading
 * - Supports cards, tables, charts, stat grids, and custom layouts
 */

class SkeletonLoader {
    /**
     * @param {object} options
     * @param {number} options.fadeMs - Fade transition duration in ms (default: 300)
     * @param {string} options.skeletonClass - Base CSS class for skeleton elements (default: 'skeleton')
     */
    constructor(options = {}) {
        this.fadeMs = options.fadeMs || 300;
        this.skeletonClass = options.skeletonClass || 'skeleton';
        this._activeSkeletons = new Map();
    }

    /**
     * Show skeleton in a container, replacing its content temporarily
     * @param {string|HTMLElement} container - Selector or element
     * @param {string} layout - Layout type: 'cards', 'table', 'stats', 'chart', 'list', 'detail', 'form', 'custom'
     * @param {object} config - Layout-specific configuration
     * @returns {string} Skeleton ID for later removal
     */
    show(container, layout = 'cards', config = {}) {
        const el = typeof container === 'string' ? document.querySelector(container) : container;
        if (!el) return null;

        const id = 'sk-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);

        // Save original content
        const originalContent = el.innerHTML;
        const originalOpacity = el.style.opacity;

        // Generate skeleton HTML
        const skeletonHtml = this._generateSkeleton(layout, config);

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'skeleton-wrapper';
        wrapper.id = id;
        wrapper.setAttribute('role', 'status');
        wrapper.setAttribute('aria-label', 'Loading...');
        wrapper.innerHTML = skeletonHtml;

        // Replace content
        el.innerHTML = '';
        el.appendChild(wrapper);

        // Store reference
        this._activeSkeletons.set(id, { el, originalContent, originalOpacity, wrapper });

        return id;
    }

    /**
     * Hide skeleton and restore/replace content with smooth transition
     * @param {string} id - Skeleton ID returned by show()
     * @param {string|null} newContent - New HTML content (null = restore original)
     */
    hide(id, newContent = null) {
        const record = this._activeSkeletons.get(id);
        if (!record) return;

        const { el, originalContent, wrapper } = record;

        // Fade out skeleton
        wrapper.style.transition = `opacity ${this.fadeMs}ms ease`;
        wrapper.style.opacity = '0';

        setTimeout(() => {
            // Remove skeleton wrapper
            if (wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);

            // Set new content or restore original
            if (newContent !== null) {
                el.innerHTML = newContent;
            } else {
                el.innerHTML = originalContent;
            }

            // Fade in new content
            el.style.opacity = '0';
            el.style.transition = `opacity ${this.fadeMs}ms ease`;
            requestAnimationFrame(() => {
                el.style.opacity = '1';
            });

            this._activeSkeletons.delete(id);
        }, this.fadeMs);
    }

    /**
     * Hide all active skeletons
     */
    hideAll() {
        for (const id of this._activeSkeletons.keys()) {
            this.hide(id);
        }
    }

    /**
     * Check if a skeleton is active
     * @param {string} id
     * @returns {boolean}
     */
    isActive(id) {
        return this._activeSkeletons.has(id);
    }

    /**
     * Generate skeleton HTML based on layout type
     * @private
     */
    _generateSkeleton(layout, config) {
        switch (layout) {
            case 'stats':
                return this._skeletonStats(config);
            case 'cards':
                return this._skeletonCards(config);
            case 'table':
                return this._skeletonTable(config);
            case 'chart':
                return this._skeletonChart(config);
            case 'list':
                return this._skeletonList(config);
            case 'detail':
                return this._skeletonDetail(config);
            case 'form':
                return this._skeletonForm(config);
            case 'dashboard':
                return this._skeletonDashboard(config);
            default:
                return this._skeletonCards(config);
        }
    }

    /**
     * Stat cards skeleton (4 cards in a row)
     * @private
     */
    _skeletonStats(config) {
        const count = config.count || 4;
        let html = `<div class="card-grid card-grid-${count}" style="margin-bottom:24px;">`;
        for (let i = 0; i < count; i++) {
            html += `
                <div class="stat-card">
                    <div class="${this.skeletonClass} skeleton-circle"></div>
                    <div style="flex:1;">
                        <div class="${this.skeletonClass} skeleton-text short" style="height:24px;margin-bottom:8px;"></div>
                        <div class="${this.skeletonClass} skeleton-text medium" style="height:12px;"></div>
                    </div>
                </div>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Card grid skeleton
     * @private
     */
    _skeletonCards(config) {
        const count = config.count || 6;
        const cols = config.cols || 3;
        let html = `<div class="card-grid card-grid-${cols}">`;
        for (let i = 0; i < count; i++) {
            html += `
                <div class="card">
                    <div class="${this.skeletonClass} skeleton-text" style="width:60%;height:18px;margin-bottom:16px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:100%;height:12px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:80%;height:12px;"></div>
                    <div class="${this.skeletonClass} skeleton-text short" style="height:12px;"></div>
                    <div style="margin-top:16px;">
                        <div class="${this.skeletonClass}" style="height:32px;width:80px;border-radius:6px;"></div>
                    </div>
                </div>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Table skeleton
     * @private
     */
    _skeletonTable(config) {
        const rows = config.rows || 8;
        const cols = config.cols || 6;
        let html = '<div class="table-container"><table class="data-table"><thead><tr>';
        for (let c = 0; c < cols; c++) {
            html += `<th><div class="${this.skeletonClass} skeleton-text" style="width:${60 + Math.random() * 40}%;height:14px;"></div></th>`;
        }
        html += '</tr></thead><tbody>';
        for (let r = 0; r < rows; r++) {
            html += '<tr>';
            for (let c = 0; c < cols; c++) {
                const w = 40 + Math.random() * 50;
                html += `<td><div class="${this.skeletonClass} skeleton-text" style="width:${w}%;height:14px;animation-delay:${r * 0.05}s;"></div></td>`;
            }
            html += '</tr>';
        }
        html += '</tbody></table></div>';
        return html;
    }

    /**
     * Chart skeleton
     * @private
     */
    _skeletonChart(config) {
        const height = config.height || 300;
        return `
            <div class="card" style="padding:24px;">
                <div class="${this.skeletonClass} skeleton-text" style="width:30%;height:18px;margin-bottom:16px;"></div>
                <div class="${this.skeletonClass}" style="width:100%;height:${height}px;border-radius:8px;"></div>
            </div>`;
    }

    /**
     * List skeleton
     * @private
     */
    _skeletonList(config) {
        const count = config.count || 6;
        let html = '<div style="display:flex;flex-direction:column;gap:12px;">';
        for (let i = 0; i < count; i++) {
            html += `
                <div style="display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg-card);border-radius:8px;border:1px solid var(--border);">
                    <div class="${this.skeletonClass} skeleton-circle" style="width:40px;height:40px;"></div>
                    <div style="flex:1;">
                        <div class="${this.skeletonClass} skeleton-text" style="width:${50 + Math.random() * 30}%;height:14px;margin-bottom:6px;"></div>
                        <div class="${this.skeletonClass} skeleton-text short" style="height:12px;"></div>
                    </div>
                    <div class="${this.skeletonClass}" style="width:60px;height:24px;border-radius:12px;"></div>
                </div>`;
        }
        html += '</div>';
        return html;
    }

    /**
     * Detail page skeleton (product detail, etc.)
     * @private
     */
    _skeletonDetail(config) {
        return `
            <div style="display:grid;grid-template-columns:1fr 2fr;gap:24px;">
                <div>
                    <div class="${this.skeletonClass}" style="width:100%;height:300px;border-radius:12px;margin-bottom:16px;"></div>
                    <div style="display:flex;gap:8px;">
                        <div class="${this.skeletonClass}" style="width:60px;height:60px;border-radius:8px;"></div>
                        <div class="${this.skeletonClass}" style="width:60px;height:60px;border-radius:8px;"></div>
                        <div class="${this.skeletonClass}" style="width:60px;height:60px;border-radius:8px;"></div>
                    </div>
                </div>
                <div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:70%;height:24px;margin-bottom:12px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:40%;height:16px;margin-bottom:24px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:100%;height:14px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:90%;height:14px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:85%;height:14px;"></div>
                    <div class="${this.skeletonClass} skeleton-text" style="width:60%;height:14px;margin-bottom:24px;"></div>
                    <div style="display:flex;gap:12px;margin-top:16px;">
                        <div class="${this.skeletonClass}" style="width:120px;height:40px;border-radius:8px;"></div>
                        <div class="${this.skeletonClass}" style="width:120px;height:40px;border-radius:8px;"></div>
                    </div>
                </div>
            </div>`;
    }

    /**
     * Form skeleton
     * @private
     */
    _skeletonForm(config) {
        const fields = config.fields || 4;
        let html = '<div class="card" style="max-width:600px;">';
        html += `<div class="${this.skeletonClass} skeleton-text" style="width:40%;height:20px;margin-bottom:24px;"></div>`;
        for (let i = 0; i < fields; i++) {
            html += `
                <div style="margin-bottom:16px;">
                    <div class="${this.skeletonClass} skeleton-text short" style="height:12px;margin-bottom:8px;"></div>
                    <div class="${this.skeletonClass}" style="width:100%;height:40px;border-radius:6px;"></div>
                </div>`;
        }
        html += `<div class="${this.skeletonClass}" style="width:120px;height:40px;border-radius:8px;margin-top:8px;"></div>`;
        html += '</div>';
        return html;
    }

    /**
     * Dashboard skeleton (stats + chart + table)
     * @private
     */
    _skeletonDashboard(config) {
        return this._skeletonStats({ count: 4 }) +
            '<div style="display:grid;grid-template-columns:2fr 1fr;gap:24px;margin-bottom:24px;">' +
            this._skeletonChart({ height: 250 }) +
            this._skeletonList({ count: 4 }) +
            '</div>' +
            this._skeletonTable({ rows: 5, cols: 6 });
    }
}

// ========== Global Skeleton Instance ==========
const skeleton = new SkeletonLoader();

/**
 * Convenience: Show skeleton and auto-hide when a promise resolves
 * @param {string|HTMLElement} container
 * @param {string} layout
 * @param {Promise} promise - The async operation
 * @param {object} config
 * @returns {Promise} The original promise result
 */
async function withSkeleton(container, layout, promise, config = {}) {
    const id = skeleton.show(container, layout, config);
    try {
        const result = await promise;
        skeleton.hide(id);
        return result;
    } catch (e) {
        skeleton.hide(id);
        throw e;
    }
}

// Export for global use
window.SkeletonLoader = SkeletonLoader;
window.skeleton = skeleton;
window.withSkeleton = withSkeleton;
