/**
 * Amazon Visionary Sourcing Tool - Empty State Components (PRD 2.2)
 *
 * Unified empty state illustrations with consistent design language:
 * - SVG-based illustrations (no external image dependencies)
 * - Contextual messages and call-to-action buttons
 * - Supports: no-data, no-results, error, no-projects, no-products, welcome
 */

class EmptyState {
    /**
     * Render an empty state into a container
     * @param {string|HTMLElement} container - Selector or element
     * @param {string} type - Type: 'no-data', 'no-results', 'error', 'no-projects', 'no-products', 'welcome', 'no-keywords', 'no-suppliers', 'no-competitors'
     * @param {object} options
     * @param {string} options.title - Custom title (optional)
     * @param {string} options.message - Custom message (optional)
     * @param {string} options.actionText - CTA button text (optional)
     * @param {function} options.onAction - CTA button click handler (optional)
     * @param {string} options.actionHref - CTA button link (optional)
     * @param {string} options.secondaryText - Secondary button text (optional)
     * @param {function} options.onSecondary - Secondary button click handler (optional)
     */
    static render(container, type = 'no-data', options = {}) {
        const el = typeof container === 'string' ? document.querySelector(container) : container;
        if (!el) return;

        const config = EmptyState._getConfig(type);
        const title = options.title || config.title;
        const message = options.message || config.message;
        const actionText = options.actionText || config.actionText;
        const actionHref = options.actionHref || config.actionHref;

        let actionsHtml = '';
        if (actionText) {
            if (actionHref) {
                actionsHtml += `<a href="${actionHref}" class="btn btn-primary">${actionText}</a>`;
            } else {
                actionsHtml += `<button class="btn btn-primary" id="empty-state-action">${actionText}</button>`;
            }
        }
        if (options.secondaryText) {
            actionsHtml += `<button class="btn btn-secondary" id="empty-state-secondary">${options.secondaryText}</button>`;
        }

        el.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-illustration">
                    ${config.svg}
                </div>
                <h3 class="empty-state-title">${title}</h3>
                <p class="empty-state-message">${message}</p>
                ${actionsHtml ? `<div class="empty-state-actions">${actionsHtml}</div>` : ''}
            </div>
        `;

        // Bind event handlers
        if (options.onAction) {
            const btn = el.querySelector('#empty-state-action');
            if (btn) btn.addEventListener('click', options.onAction);
        }
        if (options.onSecondary) {
            const btn = el.querySelector('#empty-state-secondary');
            if (btn) btn.addEventListener('click', options.onSecondary);
        }
    }

    /**
     * Get configuration for each empty state type
     * @private
     */
    static _getConfig(type) {
        const configs = {
            'no-data': {
                title: 'No Data Yet',
                message: 'Start by creating a new project or running an analysis to see data here.',
                actionText: 'Create Project',
                actionHref: '/projects/new',
                svg: EmptyState._svgNoData()
            },
            'no-results': {
                title: 'No Results Found',
                message: 'Try adjusting your search criteria or filters to find what you\'re looking for.',
                actionText: 'Clear Filters',
                actionHref: null,
                svg: EmptyState._svgNoResults()
            },
            'error': {
                title: 'Something Went Wrong',
                message: 'An unexpected error occurred. Please try again or contact support if the problem persists.',
                actionText: 'Try Again',
                actionHref: null,
                svg: EmptyState._svgError()
            },
            'no-projects': {
                title: 'No Projects Yet',
                message: 'Create your first sourcing project to start discovering profitable products.',
                actionText: 'New Project',
                actionHref: '/projects/new',
                svg: EmptyState._svgNoProjects()
            },
            'no-products': {
                title: 'No Products Found',
                message: 'Run a product search to discover potential products for your sourcing pipeline.',
                actionText: 'Search Products',
                actionHref: '/market',
                svg: EmptyState._svgNoProducts()
            },
            'welcome': {
                title: 'Welcome to Visionary',
                message: 'Your AI-powered product sourcing assistant. Get started by creating your first project.',
                actionText: 'Get Started',
                actionHref: '/projects/new',
                svg: EmptyState._svgWelcome()
            },
            'no-keywords': {
                title: 'No Keywords Analyzed',
                message: 'Run keyword research to discover high-potential search terms and competition levels.',
                actionText: 'Research Keywords',
                actionHref: '/keywords',
                svg: EmptyState._svgNoKeywords()
            },
            'no-suppliers': {
                title: 'No Suppliers Found',
                message: 'Search for suppliers on 1688 to find the best sourcing options for your products.',
                actionText: 'Find Suppliers',
                actionHref: '/suppliers',
                svg: EmptyState._svgNoSuppliers()
            },
            'no-competitors': {
                title: 'No Competitors Tracked',
                message: 'Add competitors to monitor their pricing, reviews, and market position.',
                actionText: 'Add Competitors',
                actionHref: '/competitors',
                svg: EmptyState._svgNoCompetitors()
            }
        };

        return configs[type] || configs['no-data'];
    }

    // ========== SVG Illustrations ==========

    static _svgNoData() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="30" y="40" width="120" height="90" rx="8" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <rect x="45" y="55" width="90" height="8" rx="4" fill="#334155"/>
            <rect x="45" y="70" width="70" height="8" rx="4" fill="#334155"/>
            <rect x="45" y="85" width="80" height="8" rx="4" fill="#334155"/>
            <rect x="45" y="100" width="50" height="8" rx="4" fill="#334155"/>
            <circle cx="140" cy="35" r="20" fill="rgba(99,102,241,0.15)" stroke="#6366f1" stroke-width="2"/>
            <path d="M133 35L138 40L147 31" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="45" cy="145" r="6" fill="rgba(6,182,212,0.2)"/>
            <circle cx="135" cy="145" r="4" fill="rgba(245,158,11,0.2)"/>
        </svg>`;
    }

    static _svgNoResults() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="80" cy="70" r="40" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <circle cx="80" cy="70" r="25" stroke="#6366f1" stroke-width="2" stroke-dasharray="4 4"/>
            <line x1="108" y1="98" x2="135" y2="125" stroke="#6366f1" stroke-width="4" stroke-linecap="round"/>
            <path d="M72 65L88 65" stroke="#64748b" stroke-width="2" stroke-linecap="round"/>
            <path d="M72 75L85 75" stroke="#64748b" stroke-width="2" stroke-linecap="round"/>
            <circle cx="150" cy="40" r="8" fill="rgba(245,158,11,0.15)" stroke="#f59e0b" stroke-width="1.5"/>
            <path d="M150 36V40" stroke="#f59e0b" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="150" cy="43" r="0.5" fill="#f59e0b"/>
        </svg>`;
    }

    static _svgError() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="35" y="30" width="110" height="100" rx="12" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <circle cx="90" cy="70" r="25" fill="rgba(239,68,68,0.1)" stroke="#ef4444" stroke-width="2"/>
            <path d="M82 62L98 78M98 62L82 78" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round"/>
            <rect x="55" y="105" width="70" height="8" rx="4" fill="#334155"/>
            <rect x="65" y="118" width="50" height="6" rx="3" fill="#334155"/>
            <circle cx="155" cy="45" r="5" fill="rgba(245,158,11,0.2)"/>
            <circle cx="25" cy="80" r="4" fill="rgba(99,102,241,0.2)"/>
        </svg>`;
    }

    static _svgNoProjects() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="25" y="45" width="60" height="75" rx="6" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <rect x="95" y="45" width="60" height="75" rx="6" fill="#1e293b" stroke="#334155" stroke-width="2" stroke-dasharray="6 4"/>
            <rect x="35" y="58" width="40" height="6" rx="3" fill="#334155"/>
            <rect x="35" y="70" width="30" height="6" rx="3" fill="#334155"/>
            <rect x="35" y="82" width="35" height="6" rx="3" fill="#334155"/>
            <circle cx="125" cy="75" r="12" fill="rgba(99,102,241,0.1)" stroke="#6366f1" stroke-width="2"/>
            <path d="M125 69V81M119 75H131" stroke="#6366f1" stroke-width="2" stroke-linecap="round"/>
            <path d="M55 35L55 25C55 22 57 20 60 20H80" stroke="#6366f1" stroke-width="1.5" stroke-dasharray="4 3"/>
            <circle cx="85" cy="20" r="4" fill="rgba(6,182,212,0.3)"/>
        </svg>`;
    }

    static _svgNoProducts() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="40" y="35" width="100" height="80" rx="8" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <rect x="55" y="50" width="30" height="30" rx="4" fill="rgba(99,102,241,0.1)" stroke="#6366f1" stroke-width="1.5"/>
            <rect x="95" y="50" width="30" height="6" rx="3" fill="#334155"/>
            <rect x="95" y="62" width="25" height="6" rx="3" fill="#334155"/>
            <rect x="95" y="74" width="20" height="6" rx="3" fill="rgba(34,197,94,0.3)"/>
            <rect x="55" y="90" width="70" height="8" rx="4" fill="#334155"/>
            <path d="M65 60L70 65L78 57" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="150" cy="130" r="6" fill="rgba(245,158,11,0.2)"/>
            <circle cx="30" cy="130" r="4" fill="rgba(6,182,212,0.2)"/>
        </svg>`;
    }

    static _svgWelcome() {
        return `<svg width="200" height="160" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="30" width="100" height="100" rx="12" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <path d="M75 80L90 95L125 60" stroke="#6366f1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="100" cy="80" r="35" stroke="url(#welcome-grad)" stroke-width="2" fill="none"/>
            <circle cx="40" cy="50" r="8" fill="rgba(99,102,241,0.15)"/>
            <circle cx="160" cy="50" r="6" fill="rgba(6,182,212,0.15)"/>
            <circle cx="45" cy="120" r="5" fill="rgba(245,158,11,0.15)"/>
            <circle cx="155" cy="120" r="7" fill="rgba(34,197,94,0.15)"/>
            <path d="M20 80L35 80" stroke="#334155" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M165 80L180 80" stroke="#334155" stroke-width="1.5" stroke-linecap="round"/>
            <defs><linearGradient id="welcome-grad" x1="65" y1="45" x2="135" y2="115"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#06b6d4"/></linearGradient></defs>
        </svg>`;
    }

    static _svgNoKeywords() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="30" y="40" width="120" height="35" rx="8" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <circle cx="50" cy="57" r="8" fill="rgba(99,102,241,0.15)" stroke="#6366f1" stroke-width="1.5"/>
            <rect x="65" y="53" width="70" height="8" rx="4" fill="#334155"/>
            <rect x="40" y="90" width="40" height="20" rx="10" fill="rgba(99,102,241,0.1)" stroke="#6366f1" stroke-width="1.5"/>
            <rect x="90" y="90" width="50" height="20" rx="10" fill="rgba(6,182,212,0.1)" stroke="#06b6d4" stroke-width="1.5"/>
            <rect x="55" y="120" width="45" height="20" rx="10" fill="rgba(245,158,11,0.1)" stroke="#f59e0b" stroke-width="1.5"/>
            <text x="50" y="104" font-size="8" fill="#6366f1" font-family="Inter, sans-serif">keyword</text>
            <text x="100" y="104" font-size="8" fill="#06b6d4" font-family="Inter, sans-serif">search</text>
            <text x="65" y="134" font-size="8" fill="#f59e0b" font-family="Inter, sans-serif">trend</text>
        </svg>`;
    }

    static _svgNoSuppliers() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="30" y="50" width="50" height="60" rx="6" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <rect x="100" y="50" width="50" height="60" rx="6" fill="#1e293b" stroke="#334155" stroke-width="2" stroke-dasharray="5 3"/>
            <circle cx="55" cy="70" r="10" fill="rgba(99,102,241,0.15)" stroke="#6366f1" stroke-width="1.5"/>
            <path d="M52 70L55 73L60 67" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round"/>
            <rect x="38" y="88" width="34" height="5" rx="2.5" fill="#334155"/>
            <rect x="38" y="97" width="24" height="5" rx="2.5" fill="#334155"/>
            <circle cx="125" cy="75" r="8" fill="rgba(6,182,212,0.1)" stroke="#06b6d4" stroke-width="1.5"/>
            <path d="M125 71V79M121 75H129" stroke="#06b6d4" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M80 75L100 75" stroke="#334155" stroke-width="1.5" stroke-dasharray="4 3"/>
            <polygon points="97,72 100,75 97,78" fill="#334155"/>
        </svg>`;
    }

    static _svgNoCompetitors() {
        return `<svg width="180" height="160" viewBox="0 0 180 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="60" cy="70" r="20" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <circle cx="120" cy="70" r="20" fill="#1e293b" stroke="#334155" stroke-width="2" stroke-dasharray="5 3"/>
            <circle cx="60" cy="65" r="6" fill="rgba(99,102,241,0.2)"/>
            <path d="M50 80C50 76 54 73 60 73S70 76 70 80" stroke="#6366f1" stroke-width="1.5"/>
            <circle cx="120" cy="65" r="6" fill="rgba(6,182,212,0.15)"/>
            <path d="M110 80C110 76 114 73 120 73S130 76 130 80" stroke="#06b6d4" stroke-width="1.5" stroke-dasharray="3 2"/>
            <path d="M80 70L100 70" stroke="#334155" stroke-width="1.5"/>
            <rect x="85" y="66" width="10" height="8" rx="2" fill="#1e293b" stroke="#f59e0b" stroke-width="1"/>
            <text x="87" y="73" font-size="6" fill="#f59e0b" font-family="Inter, sans-serif">VS</text>
            <rect x="35" y="105" width="110" height="25" rx="6" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
            <rect x="45" y="113" width="30" height="6" rx="3" fill="rgba(99,102,241,0.2)"/>
            <rect x="80" y="113" width="20" height="6" rx="3" fill="rgba(6,182,212,0.2)"/>
            <rect x="105" y="113" width="25" height="6" rx="3" fill="rgba(245,158,11,0.2)"/>
        </svg>`;
    }
}

// Export for global use
window.EmptyState = EmptyState;
