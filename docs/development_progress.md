# Amazon Visionary Sourcing Tool - Development Progress

> Last Updated: 2026-03-18

## Overall Status: **Production-Ready (All P0-P3 Issues Implemented)**

All 21 GitHub Issues (P0-P3) have been implemented. Frontend includes 16 pages with full i18n support (EN/ZH/KO), OAuth login, password reset, email verification, team management, notifications, and APM dashboard. Backend includes Stripe payments, rate limiting, audit logging, data export (CSV/Excel/PDF), Celery SSE, and comprehensive error handling. K8s deployment configs include Prometheus ServiceMonitor, alert rules, and Grafana dashboard. CI/CD pipeline with lint, test, and Docker build stages.

---

## Module Completion Summary

| Module | Status | Completion |
|--------|--------|------------|
| Core Pipeline Engine | Done | 100% |
| Amazon SP-API Scraper | Done | 100% |
| Keepa Independent Module | Done | 100% |
| Naver Trend Crawler | Done | 100% |
| Google Trends Integration | Done | 100% |
| AI Analysis Engine (GPT-4V) | Done | 100% |
| Review Sentiment Analysis | Done | 100% |
| Data Filtering (Rule + AI) | Done | 100% |
| Amazon Category Analyzer | Done | 100% |
| Amazon Pipeline | Done | 100% |
| 1688 Image Search | Done | 100% |
| Profit Calculator | Done | 100% |
| 3D Asset Generation API | Done | 100% |
| Video Renderer (FFmpeg) | Done | 100% |
| File Upload Parser (CSV/XLSX) | Done | 100% |
| User Auth (JWT + bcrypt) | Done | 100% |
| API Key Encryption (AES-256-GCM) | Done | 100% |
| Quota Middleware + API | Done | 100% |
| Subscription / Monetization | Done | 100% |
| Celery Async Tasks | Done | 100% |
| Chrome Extension + WebSocket | Done | 100% |
| Asset Download (ZIP) | Done | 100% |
| Docker Deployment | Done | 100% |

### Frontend Pages

| Page | Template | Route | Status |
|------|----------|-------|--------|
| Login / Register / OAuth / Reset | `auth.html` | `/auth/*` | Done |
| Dashboard | `dashboard.html` | `/dashboard` | Done |
| New Project Wizard | `new_project.html` | `/projects/new` | Done |
| Project Detail (Data Table) | `project_detail.html` | `/projects/{id}` | Done |
| Product Deep Analysis (5D Radar) | `product_analysis.html` | `/products/{asin}/analysis` | Done |
| Market & Category Analysis | `market_analysis.html` | `/market/{keyword}` | Done |
| Profit Calculator | `profit_calculator.html` | `/profit/{asin}` | Done |
| Decision Report | `report.html` | `/reports/{id}` | Done |
| 3D Lab (Three.js) | `threed_lab.html` | `/3d-lab` | Done |
| Subscription Management | `subscription.html` | `/settings/subscription` | Done |
| AI Settings | `ai_settings.html` | `/settings/ai` | Done |
| API Keys Settings | `api_keys_settings.html` | `/settings/api-keys` | Done |
| Team Management | `team.html` | `/settings/team` | Done |
| Notifications Center | `notifications.html` | `/notifications` | Done |
| APM Dashboard | `apm_dashboard.html` | `/admin/apm` | Done |

### API Routes

| Blueprint | Prefix | Status |
|-----------|--------|--------|
| Auth | `/api/auth` | Done |
| User Quota | `/api/v1/user/quota` | Done |
| Projects | `/api/v1/projects` | Done |
| Analysis | `/api/v1/analysis` | Done |
| 3D Assets | `/api/v1/3d` | Done |
| Profit/Supply | `/api/v1/profit`, `/api/v1/supply` | Done |
| Upload/Trends | `/api/v1/upload` | Done |
| Asset Download | `/api/v1/assets` | Done |
| WebSocket | `/ws/extension` | Done |
| Monetization | `/api/subscription` | Done |
| AI Config | `/api/ai` | Done |
| API Keys | `/api/keys` | Done |
| Export | `/api/v1/export` | Done |
| Team | `/api/v1/team` | Done |
| Notifications | `/api/v1/notifications` | Done |
| Stripe | `/api/v1/stripe` | Done |
| OAuth | `/api/auth/oauth` | Done |
| SSE | `/api/v1/sse` | Done |
| Audit | `/api/v1/admin/audit` | Done |
| Cleanup | `/api/v1/admin/cleanup` | Done |
| APM | `/api/v1/admin/apm` | Done |
| i18n | `/api/i18n` | Done |
| Swagger | `/api/docs` | Done |

---

## Architecture

```
Amazon Visionary Sourcing Tool
├── app.py                      # Flask application factory
├── pipeline.py                 # Core sourcing pipeline (Coupang)
├── amazon_pipeline.py          # Amazon-specific pipeline
├── celery_app.py               # Celery async task queue
├── api/                        # REST API routes
│   ├── auth_routes.py          # Auth + quota endpoint
│   ├── project_routes.py
│   ├── analysis_routes.py
│   ├── threed_routes.py
│   ├── profit_routes.py
│   ├── upload_routes.py        # File upload + Google Trends
│   ├── asset_download_routes.py # ZIP download
│   ├── websocket_handler.py    # Chrome extension WebSocket
│   ├── monetization_routes.py
│   ├── ai_config_routes.py
│   └── api_keys_routes.py
├── auth/                       # Authentication
│   ├── user_model.py
│   ├── api_keys_config.py      # AES-256-GCM encryption
│   └── quota_middleware.py
├── scrapers/                   # Data collection
│   ├── amazon/                 # Amazon SP-API + crawler
│   ├── coupang/                # Coupang crawlers
│   ├── keepa/                  # Keepa historical data
│   ├── naver/                  # Naver trend crawler
│   ├── alibaba1688/            # 1688 sourcing
│   └── google_trends.py        # Google Trends
├── analysis/                   # AI analysis engine
│   ├── ai_analyzer.py
│   ├── review_analyzer.py
│   ├── amazon_data_filter.py
│   ├── data_filter.py
│   ├── risk_scoring.py         # 5-dimension risk radar
│   ├── market_analysis/
│   ├── profit_analysis/
│   └── model_3d/
│       └── video_renderer.py
├── tasks/                      # Celery async tasks
│   ├── scraping_tasks.py
│   ├── analysis_tasks.py
│   └── threed_tasks.py
├── utils/
│   ├── file_upload_parser.py
│   ├── logger.py
│   ├── http_client.py
│   ├── error_handler.py        # Global exception handler + HTML error pages
│   ├── swagger_config.py       # OpenAPI 3.0 spec (105 paths)
│   └── data_exporter.py        # CSV/Excel/PDF export
├── frontend/
│   ├── routes.py               # Page URL routing (PRD-aligned)
│   ├── templates/ (16 pages)
│   └── static/
│       ├── css/main.css        # Dark theme + skeleton + toast
│       └── js/api.js           # API client + quota interception
├── chrome_extension/           # Chrome Manifest V3 plugin + WebSocket
├── database/
│   ├── schema.sql              # Complete DDL (31 tables)
│   └── migrations/ (8 scripts)
├── Dockerfile
├── docker-compose.yml
└── docs/
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask 3.1 |
| Frontend | Jinja2 + Vanilla JS + Chart.js + Three.js |
| Database | MySQL / TiDB |
| Cache/Queue | Redis + Celery 5.3 |
| AI | OpenAI GPT-4V / GPT-4 |
| 3D | TripoSR / Meshy API |
| Scraping | Playwright + Requests + BeautifulSoup |
| Deployment | Docker + Docker Compose + K8s + Gunicorn |
| Auth | JWT + bcrypt + AES-256-GCM |
| WebSocket | flask-sock |

---

## Changelog

### 2026-03-18 (Phase 12) - Schema Overhaul, Error Pages, Favicon & Meta
- **Database**: Rewrote `schema.sql` from 13 tables to 31 tables (complete one-stop DDL including all migration tables)
- **Database**: Added `users` table with all fields (ai_settings, subscription, oauth, email_verification)
- **Database**: Fixed migration script numbering conflict (003/004 duplicates -> 005-008 renumbered)
- **Error Pages**: Created `errors/403.html`, `errors/404.html`, `errors/500.html` with animations and dark theme
- **Error Handler**: Enhanced `_wants_json()` helper - API paths return JSON, browser requests return HTML error pages
- **Favicon**: Added SVG favicon (CS logo, purple gradient) at `/favicon.svg`
- **SEO**: Added `robots.txt` (disallow /api/, /auth, /dashboard), meta description, theme-color
- **Routes**: Added `/robots.txt` and `/favicon.svg` Flask routes in `app.py`
- **Tests**: 24/24 frontend pages pass, 51/51 Mock tests pass, 8/8 K8s YAML valid, 31 DB tables verified

### 2026-03-18 (Phase 11) - Swagger API Docs + i18n Full Coverage + Mock Tests
- **Swagger/OpenAPI 3.0**: Expanded from 13 paths to 105 paths, 115 operations, 18 tags, 8 schemas
- **i18n**: Added 45 `data-i18n` attributes across 13 frontend pages, 3 language files expanded to 186 keys each
- **Tests**: New `test_scrapers.py` (26 tests) + `test_ai_analysis.py` (25 tests) with full Mock coverage, all 51 pass
- **README**: Updated blueprint count 12→23, page count 12→16, added new tech stack, project structure, dev progress
- **Fix**: `test_all_modules.py` sys.exit wrapped in `__name__` guard for pytest compatibility
- **Cleanup**: Removed temporary files (test_merge.py, todo_remaining.md, swagger backup)

### 2026-03-18 (Phase 10) - P2/P3 Feature Completion & Production Readiness
- **New Page**: `auth.html` fully rewritten with OAuth (Google/GitHub), forgot password, reset password, email verification panels
- **New Page**: `team.html` - Team management with member invite, role assignment, activity log
- **New Page**: `notifications.html` - Notification center with filters, mark read, preferences
- **New Page**: `apm_dashboard.html` - APM monitoring with Chart.js charts, health status, slow queries, endpoint metrics
- **New Route**: `/auth/forgot-password`, `/auth/reset-password`, `/auth/verify-email` frontend routes
- **New Route**: `/admin/apm` APM dashboard frontend route
- **Backend**: Added report PDF export route in `export_routes.py` + `data_exporter.py`
- **Backend**: Added notification PUT routes (mark read, mark all read, update preferences)
- **Frontend**: Added notification bell + language switcher dropdown to `base.html` top bar
- **Frontend**: Added `data-i18n` attributes to all sidebar nav items and dashboard stat labels
- **Frontend**: Added `exportBackend()` function for Excel/PDF export in `project_detail.html`
- **i18n**: Added missing nav keys (new_project, subscription, team) to all 3 UI locale files
- **i18n**: Added dashboard section keys (subtitle, active_projects, etc.) to all 3 UI locale files
- **CSS**: Enhanced responsive design - mobile sidebar overlay, table scroll, iOS zoom fix, auth page mobile
- **K8s**: Updated `web.yaml` labels to match ServiceMonitor selector (app=avst, component=web)
- **K8s**: Added `monitoring.yaml` with Prometheus ServiceMonitor, PrometheusRule alerts, Grafana dashboard ConfigMap
- **Tests**: 19/19 frontend pages pass, 16 templates parse without errors, all K8s YAML valid

### 2026-03-18 (Phase 9) - Frontend-Backend Contract Alignment & UI Enhancement
- **Critical Fix**: `api.js` login method now correctly reads `data.access_token` (was checking non-existent `result.token`)
- **Critical Fix**: `api.js` login sends `login_id` parameter (was sending `email`, backend expects `login_id`)
- **Critical Fix**: `auth.html` login form now supports username or email (matching backend `login_id`)
- Fixed `base.html` getProfile data unpacking: `{data: user}` not `{user: ...}`
- Fixed `dashboard.html` projects data unpacking: `{data: {projects}}` not `{projects}`
- Fixed `market_analysis.html` token key: `auth_token` not `token` (2 places)
- Fixed `report.html` token key: `auth_token` not `token` (2 places)
- Fixed `report.html` Top Products table column alignment with actual API data fields
- Fixed `report.html` getProject data unpacking
- Fixed `new_project.html` createProject response data unpacking
- Fixed `project_detail.html` getProject/getProducts data unpacking
- Fixed `project_detail.html` report link: `/reports/{id}` not `/report/{id}`
- Fixed `subscription.html` method name: `getMySubscription()` not `getSubscription()`
- Fixed `subscription.html` subscription/usage data unpacking
- Implemented missing `project_detail.html` functions: `exportData()`, `sortTable()`, `applyAIFilter()`, `prevPage()`, `nextPage()`, `updatePagination()`
- Updated `subscription.html` plan cards to match backend: free/orbit/moonshot with correct pricing ($0/$29.99/$99.99)
- Added `subscription.html` Quota Overview with dynamic progress bars
- Enhanced `subscription.html` Usage History with real API integration
- Added dynamic current plan highlighting in subscription page
- Saved `refresh_token` to localStorage on login

### 2026-03-18 (Phase 8) - Page Refactoring & Backend Integration
- Refactored `ai_settings.html` to inherit `base.html` template (consistent sidebar/nav)
- Refactored `api_keys_settings.html` to inherit `base.html` template
- Enhanced `profit_calculator.html`: added backend API calculation (precise FBA fees), save/history, 1688 keyword search, return rate, image preview
- Added `POST /api/v1/profit/save` and `GET /api/v1/profit/history` endpoints for calculation persistence
- Fixed `api.js` `batchCalculateProfit` parameter name mismatch (`items` -> `products`)
- Fixed `ai_settings.js` token key inconsistency (`auth_token` alignment)

### 2026-03-18 (Phase 7) - Frontend-Backend Route Alignment
- Fixed `api.js` `createProject` path (`/v1/projects` -> `/v1/projects/create`)
- Fixed `api.js` `filterProducts` path (`/v1/projects/{id}/filter` -> `/v1/projects/{id}/filter/rules`)
- Added `POST /projects/{id}/filter/rules` rule-based filtering endpoint
- Added `GET /analysis/product/{asin}` single product detail + risk radar API
- Added `GET /dashboard/activities` aggregated activity list API
- Fixed `product_analysis.html` auto-load product data and risk scores
- Fixed `dashboard.html` activity list to call real API

### 2026-03-18 (Phase 6) - Core API Persistence & Data Integration
- Rewrote `project_routes.py`: memory storage -> database persistence + Celery async tasks
- Rewrote `analysis_routes.py`: memory storage -> database persistence + Celery async tasks
- Added `/api/v1/analysis/market` market aggregation API (GMV, CR3, price distribution)
- Added `/api/v1/analysis/report/{project_id}` report generation API
- Rewrote `market_analysis.html`: hardcoded data -> backend API integration
- Rewrote `report.html`: hardcoded scores -> backend API integration
- Added 11 new integration tests (Project API + Analysis API)

### 2026-03-18 (Phase 5) - Quality Hardening & Security Audit
- Fixed `login_required` decorator: added `g.user_id` + `current_user` parameter passing
- Fixed `quota_middleware`: corrected quota_type to features key mapping
- Fixed `upload_routes.py`: `token_required` -> `login_required` import
- Added `dashboard_routes.py` with stats + activity chart APIs
- Rewrote `threed_routes.py`: memory -> database persistence
- Rewrote `threed_tasks.py`: placeholder -> real VideoRenderer
- Fixed `threed_lab.html` field name mismatches
- Fixed `dashboard.html` activity chart to use real API data
- Added 31 API integration tests (total 51 tests)
- Security: production key detection, Docker port restrictions, enhanced .gitignore
- Rewrote README.md with complete feature documentation

### 2026-03-18 (Phase 4) - Code Quality & Module Refinements
- Added independent Keepa client module (`scrapers/keepa/keepa_client.py`) with BSR history, price tracking, sales estimation, deal detection
- Generated Chrome extension icons (16/48/128px PNG) for `chrome_extension/icons/`
- Enhanced Dashboard page: quota progress bars, activity chart (Chart.js), recent projects table, quick action cards
- Upgraded database init script: migration tracking table, `--check`/`--migrate` CLI flags, idempotent execution
- Implemented PRD 3.2.2 30-day normalization formula in `amazon_data_filter.py`: Sales_30D, Revenue_30D, Clicks_30D, CVR_30D, Review_Velocity, Normalized_Score (0-100) with Min-Max weighted scoring
- Restructured tests: moved `test_*.py` to `tests/` directory, added `conftest.py` with shared fixtures

### 2026-03-18 (Phase 3) - P0/P1 Refinements Complete
- **P0-1**: Upgraded API key encryption from Base64 to AES-256-GCM (PRD 2.2)
- **P0-2**: Added top status bar with API health indicator, global search, site selector, user avatar
- **P0-2**: Added skeleton loading screens and toast notification system
- **P0-3**: Added `/api/auth/quota` and `/api/v1/user/quota` endpoints (PRD 8.1)
- **P0-4**: Aligned frontend routes with PRD (`/market/{keyword}`, `/profit/{asin}`)
- **P0-5**: Added asset download ZIP API (`/api/v1/assets/download/`)
- **P0-6**: Added frontend quota interception in API client
- **P1-7**: Enhanced sidebar navigation with all PRD pages
- **P1-9**: Added global skeleton screens and loading states
- **P1-10**: Added Chrome extension WebSocket communication (bidirectional)
- **P1-11**: Added five-dimension risk radar chart (Competition/Demand/Profit/IP/Seasonality)
- Added WebSocket server handler (`api/websocket_handler.py`)
- Updated `requirements.txt` with `flask-sock`

### 2026-03-18 (Phase 2) - Feature Complete (MVP)
- Added 10 new frontend pages (auth, dashboard, project, analysis, market, profit, 3D lab, report, subscription)
- Added base template with sidebar navigation
- Added global CSS theme (dark mode, design system)
- Added API client JS module
- Added frontend route registration (`frontend/routes.py`)
- Added file upload parser (CSV/XLSX with auto column mapping)
- Added Google Trends integration (`scrapers/google_trends.py`)
- Added video renderer service (`analysis/model_3d/video_renderer.py`)
- Added upload API routes (`api/upload_routes.py`)
- Updated `app.py` with all blueprint registrations
- Updated `requirements.txt` with all dependencies

### 2026-03-17 - Core API & Infrastructure
- Added project/analysis/3D/profit API routes
- Added Naver trend crawler implementation
- Added quota middleware
- Added Celery async task queue with scraping/analysis/3D tasks
- Added Chrome extension (Manifest V3)
- Added Docker deployment config (Dockerfile + docker-compose.yml)
- Added database migration scripts (projects, assets, analysis tables)
- Added Amazon-specific pipeline

### Earlier - Core Engine
- Implemented 10-step sourcing pipeline
- Built Amazon/Coupang/Keepa/1688 scrapers
- Built AI analysis engine (visual + review)
- Built profit calculator with sensitivity analysis
- Built report generator
- Implemented user auth system (JWT + bcrypt)
- Implemented subscription/monetization system
- Created database schema (13+ tables)
