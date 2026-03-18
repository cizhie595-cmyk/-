# Amazon Visionary Sourcing Tool - Development Progress

> Last Updated: 2026-03-18

## Overall Status: **MVP Feature Complete (All PRD Modules Implemented)**

All modules defined in the PRD have been implemented, including all P0 and P1 refinements. All frontend pages inherit the base template with consistent navigation. All API routes use database persistence with graceful degradation. The system is ready for integration testing and deployment.

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
| Login / Register | `auth.html` | `/auth` | Done |
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
│   └── http_client.py
├── frontend/
│   ├── routes.py               # Page URL routing (PRD-aligned)
│   ├── templates/ (12 pages)
│   └── static/
│       ├── css/main.css        # Dark theme + skeleton + toast
│       └── js/api.js           # API client + quota interception
├── chrome_extension/           # Chrome Manifest V3 plugin + WebSocket
├── database/
│   ├── schema.sql
│   └── migrations/ (4 scripts)
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
| Deployment | Docker + Docker Compose + Gunicorn |
| Auth | JWT + bcrypt + AES-256-GCM |
| WebSocket | flask-sock |

---

## Changelog

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
