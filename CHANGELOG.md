# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.0] - 2026-03-19

### Phase 20 - 商业化与报告增强

#### Added
- **DEV-01**: 1688/阿里妈妈返佣 - affiliate.py 新增 1688 平台支持，阿里妈妈 PID 推广位植入，淘宝客 API 集成
- **DEV-02**: 第三方服务商推荐卡片 - 新增 `monetization/service_recommendations.py`，支持 IP/商标/物流/合规/质检 5 大类服务商推荐，含返佣链接
- **DEV-03**: report.html 五维风险雷达图 - Chart.js radar chart，竞争/需求/利润/知识产权/季节性五维可视化
- **DEV-04**: report.html Markdown 渲染 - marked.js CDN 引入，综合决策报告完整 Markdown 渲染，代码高亮
- **DEV-05**: subscription.html Stripe 支付集成 - Stripe.js Checkout Session，年/月计费切换，支付历史，回调处理，处理中模态框
- **DEV-06**: Chrome 插件统计面板增强 - 今日/本周/本月时间切换，Canvas 迷你趋势图，数值动画，趋势百分比指示器，90天历史存储

#### Changed
- `monetization/affiliate.py`: 重写为支持 Amazon/Coupang/1688 三平台返佣
- `frontend/templates/report.html`: 312 → 740 行（+428 行）
- `frontend/templates/subscription.html`: 259 → 448 行（+189 行）
- `chrome_extension/popup.html`: 371 → 440 行（+69 行）
- `chrome_extension/popup.js`: 293 → 540 行（+247 行）

## [1.9.0] - 2026-03-19
### Added - Phase 19: Complete ORM Model Layer (26 New Models)
- **models_user.py**: UserModel (15 methods) + UserOAuthModel (5 methods) - User auth, OAuth, subscription, API keys, AI settings
- **models_project.py**: SourcingProjectModel (8 methods) + ProjectProductModel (7 methods) + AnalysisTaskModel (8 methods) - Project lifecycle, product management, async task tracking
- **models_analysis.py**: CategoryModel (5 methods) + MonthlySummaryModel (3 methods) + ProductImageModel (4 methods) + ReviewAnalysisModel (2 methods) + DetailPageAnalysisModel (2 methods) + ProfitAnalysisModel (3 methods) + TrendDataModel (3 methods) + AnalysisReportModel (5 methods) + ProfitCalculationModel (3 methods) + Asset3DModel (6 methods) - Full analysis data persistence
- **models_system.py**: CrawlLogModel (6 methods) + ApiUsageLogModel (4 methods) + UsageRecordModel (3 methods) + SubscriptionLogModel (3 methods) + AffiliateClickModel (3 methods) + SystemConfigModel (4 methods) + AuditLogModel (4 methods) + NotificationModel (7 methods) + TeamModel (6 methods) + TeamMemberModel (6 methods) + TeamInvitationModel (6 methods) + MigrationModel (3 methods)
- Updated `database/__init__.py` to export all 32 model classes covering 31 schema.sql tables
- 149 new test cases for all ORM models (all passing)

## [1.8.0] - 2026-03-19

### Added - Phase 18: Product Analysis Deep Enhancement
- **PA-01**: Variant Sales Donut Chart - Color/Size variant distribution with Chart.js doughnut + custom legend
- **PA-02**: Product Lifecycle Card - Estimated launch date, product age, lifecycle stage (Launch/Growth/Maturity/Decline), review velocity
- **PA-03**: Find Suppliers Button + 1688 Image Search - Supplier results panel with image, price, MOQ, score, location
- **PA-04**: Generate 3D Model Button - Quick navigation to 3D Lab with pre-filled product image and ASIN
- **PA-05**: Visual Analysis Complete Results - Marketing Structure, Text Semantic/USP, Color Psychology, Font Hierarchy, Brand Positioning cards
- **PA-06**: Fake Review Filter Stats - Suspected fake rate, authentic vs filtered count, filter reasons breakdown
- New "Suppliers" tab in product analysis page with full supplier card layout
- Enhanced `switchAnalysisTab()` to support 5 tabs (visual/reviews/bsr/competitors/suppliers)
- 54 new test cases for all PA features (all passing)

## [1.7.0] - 2026-03-19

### Added
- F-01: Scrape Depth selector in `new_project.html` - Top 50/100/200 radio cards + range slider, default Top 100, depth value sent in project creation
- F-02: Quick filter panel in `project_detail.html` - Price range, review count range, monthly sales min, BSR max, rating chips (4.5+/4.0+/3.5+/3.0+), FBA/FBM filter, brand exclude tags with "x" removal
- F-03: AI filter Textarea panel in `project_detail.html` - Replaced `prompt()` dialog with collapsible Textarea + Apply button, example prompts in placeholder
- F-04: CSV field mapping confirmation modal in `new_project.html` - Auto-detect columns, dropdown field mapping, data preview table, edit mapping link, mapping sent in project creation
- F-05: Enhanced data table in `project_detail.html` - Sticky header, horizontal scroll, column resize handles (drag to resize), column visibility toggle menu with checkboxes
- F-06: 3D generation progress ring in `threed_lab.html` - SVG circular progress with gradient fill, percentage display, 12 rotating fun messages, fullscreen overlay with backdrop blur
- F-07/F-08: Dimension selector UI in `product_analysis.html` - Active dimension tags with "x" removal, category-based recommended dimensions, all available dimensions picker, custom dimension input, dimensions passed to visual analysis API
- `tests/test_frontend_features.py` with 69 test cases covering all 8 features + CSS integration

### Changed
- `new_project.html`: Added scrape depth selector, CSV field mapping modal, scrape_depth and column_mapping in project creation data
- `project_detail.html`: Added advanced filter panel, AI filter textarea, enhanced table with sticky header/resize/column visibility
- `threed_lab.html`: Added progress ring overlay with fun messages, integrated into pollGeneration flow
- `product_analysis.html`: Added dimension selector panel with 16 predefined + custom dimensions, category recommendations for Electronics/Home/Beauty/Toys
- `main.css`: Added styles for filter panel, AI filter, table enhancements, progress ring, dimension selector
- Project stats: 377 files, 68,276 lines of code

## [1.6.0] - 2026-03-19

### Added
- GAP-01: Enhanced API status indicator with real connectivity testing, three-state lights (green/yellow/red), tooltip popups, auto-refresh every 5 minutes
- GAP-02: `frontend/static/js/image_preprocessor.js` - Canvas-based image preprocessing (1024x1024 resize, remove-bg API + client-side fallback, preview widget)
- GAP-03: `frontend/static/js/skeleton_loader.js` - Global skeleton screen loading (8 layouts: cards/table/stats/chart/list/detail/form/dashboard, fade transitions)
- GAP-04: `frontend/static/js/empty_states.js` - Unified empty state SVG illustrations (9 types: no-data/no-results/error/no-projects/no-products/welcome/no-keywords/no-suppliers/no-competitors)
- GAP-05: First-screen performance optimization (CDN preconnect/prefetch, critical CSS inlining, resource preloading, Gzip compression, cache headers, security headers)
- `tests/test_gap_features.py` with 51 test cases covering all 5 GAP features
- Image preprocessor integrated into 3D Lab (threed_lab.html) with preview widget

### Changed
- `base.html`: Added preconnect/dns-prefetch hints, preload directives, inline critical CSS, skeleton_loader.js and empty_states.js global loading
- `app.py`: Added after_request middleware for Cache-Control, security headers, Gzip compression via flask-compress
- `main.css`: Added styles for image preprocessor widget, skeleton loader enhancements, empty state components, API status tooltips
- `threed_lab.html`: Integrated ImagePreprocessor with preview widget and preprocessed blob upload
- Project stats: 375 files, 67,026 lines of code

## [1.5.0] - 2026-03-19

### Added
- `analysis/ai_analyzer.py` - Unified AI Analyzer entry module integrating DetailPageAnalyzer, ReviewAnalyzer, RiskAnalyzer, and AIProductSummarizer with full_analysis(), batch_analyze() methods
- `analysis/review_analyzer.py` - Top-level review analyzer with ReviewStatistics (rating distribution, review trends, suspicious detection, keyword frequency) and ReviewBatchAnalyzer (batch analysis, cross-product comparison)
- `analysis/risk_scoring.py` - Five-dimension risk radar (Competition, Demand, Profit, IP Risk, Seasonality) with FiveDimensionRadar class, Chart.js compatible output, weighted scoring, and batch_score()
- `analysis/profit_analysis/amazon_fba_calculator.py` - Backward-compatible alias module for AmazonFBAProfitCalculator
- Updated `analysis/__init__.py` with comprehensive module documentation
- `tests/test_missing_modules.py` with 44 test cases covering all new modules and full import verification of 23 analysis modules

### Changed
- Project stats: 253 files, 66,582 lines of code (up from 285 files*, 61,742 lines)
  *File count decreased due to cleanup of duplicate/unused files

## [1.4.0] - 2026-03-19

### Added
- Coupang Pipeline (`pipeline.py`) enhanced with 7 new analysis modules achieving feature parity with Amazon Pipeline
- Step 3.5: KeywordResearcher integration - keyword difficulty scoring, search volume estimation, long-tail keyword discovery
- Step 4.5: BSRTracker + CompetitorFinder integration - BSR ranking snapshots, competitive landscape analysis, market gap identification
- Step 5.5: SentimentVisualizer integration - review sentiment analysis, word cloud generation, tag extraction
- Step 8.5: SupplierScorer integration - multi-dimension 1688 supplier evaluation (credibility, capability, service, price, logistics)
- Step 9.5: PricingOptimizer integration - price elasticity analysis, strategy comparison (penetration/competitive/premium/skimming)
- Step 9.8: ProductDecisionEngine integration - AI-powered Go/No-Go decision scoring with comprehensive data aggregation
- Step 10 Enhanced: DashboardAnalytics data aggregation + enhanced report generation with all new module data
- 7 report formatting methods for enhanced Markdown report generation
- `skip_enhanced` parameter in pipeline `run()` for backward compatibility
- Coupang KR marketplace option in `new_project.html`, `competitor_monitor.html`, `keyword_research.html`, `pricing_strategy.html`
- Dynamic pipeline steps display in `new_project.html` that adapts to selected marketplace (Amazon vs Coupang)
- Multi-currency support (KRW/USD/EUR/GBP/JPY) in pricing strategy page
- `test_coupang_pipeline_enhanced.py` with 44 comprehensive test cases

### Fixed
- `_format_supplier_section` dict/number compatibility bug in dimension score extraction
- `save_raw_data()` now includes all 7 enhanced analysis data fields

## [1.3.0] - 2026-03-18

### Added
- `gunicorn.conf.py` production WSGI configuration with auto-scaling workers
- `Makefile` with 25+ command shortcuts (dev, test, lint, docker, k8s)
- `pytest.ini` with custom markers and test configuration
- 5 new test suites: auth, export, team, notification, stripe routes
- `LICENSE` (MIT), `CONTRIBUTING.md`, `CHANGELOG.md`
- K8s `PodDisruptionBudget` for zero-downtime rolling updates
- K8s `NetworkPolicy` for pod-level network isolation
- K8s `CronJob` for automated data cleanup
- Frontend i18n coverage for all 16 pages
- Chrome Extension enhanced popup with statistics dashboard
- SSE heartbeat mechanism and multi-channel support
- Rate limit remaining quota display in frontend header

### Fixed
- `notification_routes.py` preferences now persisted to database
- `stripe_handler.py` payment failure now sends email notification
- `video_renderer.py` silent exception handling replaced with logging
- `detail_crawler.py` 5 silent `pass` blocks replaced with debug logging
- Dockerfile updated to use gunicorn instead of `python app.py`

## [1.2.0] - 2026-03-18

### Added
- Complete `schema.sql` with all 31 database tables
- Error pages: 403 (amber), 404 (purple pulse), 500 (red shake)
- Smart error handler: JSON for API, HTML for browser requests
- SVG favicon with CS logo
- `robots.txt` with SEO configuration
- `base.html` meta tags (description, theme-color, viewport)

### Fixed
- Database migration script numbering conflict (003/004 duplicates)

## [1.1.0] - 2026-03-18

### Added
- Swagger/OpenAPI documentation expanded from 13 to 105 paths (115 operations)
- i18n `data-i18n` attributes added to base.html and dashboard.html
- 51 Mock test cases for scrapers and AI analysis modules
- README updated with accurate blueprint/page counts

### Fixed
- `test_all_modules.py` compatibility with pytest (removed `sys.exit`)

## [1.0.0] - 2026-03-18

### Added
- Notification bell and language switcher in top navigation bar
- Report PDF export route (`/api/export/report/<id>/pdf`)
- Team management page (`team.html`) with invite, role management
- Notifications center page (`notifications.html`) with filtering
- APM monitoring dashboard (`apm_dashboard.html`) with Chart.js
- Notification PUT routes (mark read, mark all read, preferences)
- Backend export buttons (Excel/PDF) in project detail page
- Sidebar navigation links for Team and Notifications

### Fixed
- Login token not saved (backend returns `data.access_token`, frontend checked `result.token`)
- Login parameter mismatch (backend expects `login_id`, frontend sent `email`)
- Auth form restricted to email only (now supports username or email)
- Data unpacking issues across 8 frontend pages
- Report link path (`/report/` → `/reports/`)
- Subscription method name (`getSubscription` → `getMySubscription`)
- Token key inconsistency (`token` → `auth_token`) in market_analysis and report pages
- Top Products table column alignment in report.html
- Subscription plan cards updated to match backend (free/orbit/moonshot)

## [0.9.0] - 2026-03-17

### Added
- Feature branch `feature/p0-improvements` merged to main
- Stripe payment integration (checkout, webhook, billing portal)
- Email verification and password reset flow
- Rate limiting middleware with Redis backend
- `.env.example` with all configuration variables
- Enhanced error handling with custom exception classes
- Database connection pooling
- Audit logging system
- Real-time SSE push notifications
- OAuth login (Google, GitHub)
- Responsive CSS for mobile devices
- Data export (CSV, Excel, PDF)
- Team collaboration backend
- Notification system backend
- Data cleanup utilities
- API documentation (Swagger)
- i18n backend with en/zh/ko locales
- K8s deployment manifests
- APM monitoring with Prometheus metrics
- CI/CD GitHub Actions workflow

## [0.8.0] - 2026-03-16

### Added
- Initial MVP release
- Flask application with 12 API blueprints
- 12 frontend pages (dashboard, projects, market analysis, etc.)
- Amazon/Coupang scraper modules
- AI-powered product analysis engine
- 3D model visualization (Three.js)
- Profit calculator
- Subscription management
- Chrome Extension for product data capture
