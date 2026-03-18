# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
