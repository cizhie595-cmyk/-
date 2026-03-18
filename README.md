# Coupang 跨境电商智能选品系统

> Amazon Visionary Sourcing Tool / 쿠팡 크로스보더 상품 선정 시스템

## 系统概述

本系统是一套面向 **Coupang（韩国酷澎）及 Amazon** 跨境电商卖家的**智能选品分析工具**，覆盖从数据采集、筛选、AI 分析、3D 建模到利润核算的完整选品流程。系统提供 Web 可视化界面、RESTful API、Chrome 浏览器扩展三种使用方式。

支持 **中文 / English / 한국어** 三种语言。

## 功能架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    app.py (Flask 应用工厂)                         │
│                    pipeline.py / amazon_pipeline.py (主流程控制器)  │
├──────────────────────────────────────────────────────────────────┤
│  scrapers/                       │  analysis/                     │
│  ├── coupang/ (搜索/详情/评论/后台) │  ├── ai_analysis/              │
│  ├── amazon/ (SP-API/搜索/详情/   │  │   ├── review_analyzer        │
│  │    评论/深爬/第三方API)         │  │   ├── detail_analyzer        │
│  ├── keepa/ (BSR/价格/销量历史)   │  │   └── risk_analyzer          │
│  ├── naver/ (搜索趋势)           │  ├── profit_analysis/           │
│  ├── alibaba1688/ (以图搜货)     │  ├── market_analysis/           │
│  └── google_trends.py            │  └── model_3d/ (3D生成+视频渲染) │
├──────────────────────────────────────────────────────────────────┤
│  api/ (23个蓝图)   │  auth/ (JWT+AES)  │  frontend/ (16个页面)     │
│  tasks/ (Celery)   │  monetization/    │  chrome_extension/        │
│  database/         │  i18n/            │  docker/                  │
└──────────────────────────────────────────────────────────────────┘
```

## 核心功能模块

### 数据采集（15 个爬虫）

| 爬虫 | 说明 |
|------|------|
| Coupang 搜索爬虫 | 输入韩文关键词，爬取 Coupang 搜索结果列表 |
| Coupang 详情爬虫 | 爬取产品详情页（图片、规格、配送方式） |
| Coupang 评论爬虫 | 爬取评论，内置刷单检测算法 |
| Coupang 后台爬虫 | 模拟登录 Wing 后台，获取运营数据 |
| Amazon 搜索爬虫 | Amazon 搜索结果抓取 |
| Amazon 详情爬虫 | Amazon 产品详情页抓取 |
| Amazon 评论爬虫 | Amazon 评论数据抓取 |
| Amazon 深度爬取 | 多维度深度数据采集 |
| Amazon SP-API | 官方 SP-API 接口对接 |
| Amazon 第三方 API | 第三方数据服务对接 |
| Keepa 客户端 | BSR 历史、价格追踪、销量估算、Deal 检测 |
| 1688 以图搜货 | 图片搜索供应商 |
| 1688 关键词搜货 | 关键词搜索供应商 |
| Naver 趋势 | 韩国 Naver 搜索趋势数据 |
| Google Trends | 全球 Google 搜索趋势 |

### AI 分析引擎（13 个分析器）

| 分析器 | 说明 |
|--------|------|
| 评论情感分析 | GPT 提取卖点/痛点/人群画像/改进建议 |
| 详情页语义分析 | GPT Vision 分析页面逻辑/视觉/信任锚点 |
| OCR 文字提取 | 产品图片文字识别 |
| AI 风险雷达 | 五维风险评估（竞争/需求/利润/IP/季节性） |
| AI 数据筛选 | 规则 + AI 双重智能过滤 |
| 类目趋势分析 | GMV 预估 + 垄断程度 + 新品占比 |
| 报告生成器 | 多语言 Markdown 决策报告 |
| 利润计算器 | FBA 利润核算 + 敏感性分析 + 定价策略对比 |
| 3D 模型生成 | 2D 图片转 3D 模型（TripoSR/Meshy） |
| 视频渲染器 | 3D 模型运镜视频渲染（FFmpeg） |
| AI 选品总结 | 综合评分 + 决策建议 |
| 30 天标准化 | Sales_30D/Revenue_30D/CVR_30D 归一化评分 |
| Amazon 数据筛选 | Amazon 专用数据清洗与筛选 |

### Web 前端（16 个页面）

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录/注册 | `/auth` | JWT 认证 |
| 仪表盘 | `/dashboard` | 统计概览 + 活动图表 + 额度进度 |
| 新建项目 | `/projects/new` | 项目创建向导 |
| 项目详情 | `/projects/{id}` | 数据表格 + 操作面板 |
| 产品分析 | `/products/{asin}/analysis` | 5D 雷达图 + 深度分析 |
| 市场分析 | `/market/{keyword}` | 类目趋势 + 竞争格局 |
| 利润计算 | `/profit/{asin}` | FBA 利润 + 敏感性分析 |
| 决策报告 | `/reports/{id}` | 综合报告导出 |
| 3D 实验室 | `/3d-lab` | Three.js 3D 模型预览 + 视频渲染 |
| 订阅管理 | `/settings/subscription` | 三档订阅计划 |
| AI 设置 | `/settings/ai` | AI 服务商配置 |
| AI 密钥 | `/settings/api-keys` | 第三方 API 密钥管理 |
| 团队管理 | `/settings/team` | 团队协作 + 成员管理 |
| 通知中心 | `/notifications` | 站内通知 + 偏好设置 |
| APM 监控 | `/admin/apm` | 系统性能监控面板 |
| API 文档 | `/api/docs` | Swagger/OpenAPI 交互式文档 |

### REST API（23 个蓝图）

| 蓝图 | 前缀 | 说明 |
|------|------|------|
| Auth | `/api/auth` | 用户注册/登录/刷新/信息管理 |
| User Quota | `/api/v1/user/quota` | 额度查询 |
| Dashboard | `/api/v1/dashboard` | 仪表盘统计 + 活动图表 |
| Projects | `/api/v1/projects` | 选品项目 CRUD + 抓取 |
| Analysis | `/api/v1/analysis` | 视觉分析 + 评论分析 + 报告 |
| 3D Assets | `/api/v1/3d` | 3D 生成 + 视频渲染 + 资产管理 |
| Profit/Supply | `/api/v1/profit`, `/api/v1/supply` | 利润计算 + 1688 搜货 |
| Upload | `/api/v1/upload` | 文件上传 + Google Trends |
| Asset Download | `/api/v1/assets` | ZIP 打包下载 |
| WebSocket | `/ws/extension` | Chrome 扩展双向通信 |
| Monetization | `/api/subscription` | 订阅管理 + Affiliate |
| AI Config | `/api/ai` | AI 服务商配置 |
| API Keys | `/api/keys` | 第三方 API 密钥加密存储 |
| OAuth | `/api/oauth` | Google/GitHub 第三方登录 |
| Stripe | `/api/stripe` | Stripe 支付集成 |
| Teams | `/api/v1/teams` | 团队协作管理 |
| Notifications | `/api/v1/notifications` | 站内通知系统 |
| Export | `/api/v1/export` | 数据导出（CSV/Excel/PDF） |
| Audit | `/api/audit` | 操作审计日志 |
| SSE | `/api/sse` | Server-Sent Events 实时推送 |
| i18n | `/api/i18n` | 国际化语言包 API |
| Swagger | `/api/docs` | OpenAPI 3.0 交互式文档 |
| APM | `/api/v1/admin/apm` | 性能监控数据 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 + Flask 3.1 |
| 前端 | Jinja2 + Vanilla JS + Chart.js + Three.js |
| 数据库 | MySQL / TiDB |
| 缓存/队列 | Redis + Celery 5.3 |
| AI | OpenAI GPT-4V / GPT-4 |
| 3D | TripoSR / Meshy API |
| 爬虫 | Playwright + Requests + BeautifulSoup |
| 部署 | Docker + Docker Compose + K8s + Gunicorn |
| 认证 | JWT + bcrypt + AES-256-GCM + OAuth 2.0 |
| 支付 | Stripe Checkout + Customer Portal |
| 监控 | Prometheus + Grafana + APM |
| WebSocket | flask-sock |

## 快速开始

### 1. 环境要求

- Python 3.10+
- MySQL 8.0+（可选，系统支持内存模式降级运行）
- Redis（可选，Celery 异步任务需要）
- FFmpeg（可选，3D 视频渲染需要）

### 2. 安装依赖

```bash
git clone https://github.com/cizhie595-cmyk/-.git
cd -

pip install -r requirements.txt

# 安装浏览器驱动（爬虫功能需要）
playwright install chromium
```

### 3. 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 填入数据库信息、API Key 等
```

### 4. 初始化数据库（可选）

```bash
python database/init_db.py

# 检查迁移状态
python database/init_db.py --check

# 执行迁移
python database/init_db.py --migrate
```

### 5. 运行

```bash
# Web 服务器模式（推荐）
python app.py --host 0.0.0.0 --port 5000

# 命令行模式（Coupang 选品）
python main.py --keyword "무선 이어폰" --lang zh_CN

# Docker 部署
docker-compose up -d
```

## 项目结构

```
coupang-product-selection/
├── app.py                           # Flask 应用工厂
├── pipeline.py                      # Coupang 主流程控制器
├── amazon_pipeline.py               # Amazon 主流程控制器
├── celery_app.py                    # Celery 异步任务配置
├── main.py                          # 命令行入口
├── requirements.txt                 # Python 依赖
├── Dockerfile                       # Docker 镜像
├── docker-compose.yml               # Docker Compose 编排
│
├── api/                             # REST API 路由（23 个蓝图）
│   ├── auth_routes.py               # 认证 + 额度
│   ├── dashboard_routes.py          # 仪表盘统计 + 活动图表
│   ├── project_routes.py            # 选品项目管理
│   ├── analysis_routes.py           # AI 分析任务
│   ├── threed_routes.py             # 3D 资产管理（数据库持久化）
│   ├── profit_routes.py             # 利润计算 + 1688 搜货
│   ├── upload_routes.py             # 文件上传 + Google Trends
│   ├── asset_download_routes.py     # ZIP 打包下载
│   ├── websocket_handler.py         # Chrome 扩展 WebSocket
│   ├── monetization_routes.py       # 订阅 + Affiliate
│   ├── ai_config_routes.py          # AI 服务商配置
│   ├── api_keys_routes.py           # 第三方 API 密钥
│   ├── oauth_routes.py              # OAuth 第三方登录
│   ├── stripe_routes.py             # Stripe 支付
│   ├── team_routes.py               # 团队协作
│   ├── notification_routes.py       # 通知系统
│   ├── export_routes.py             # 数据导出
│   ├── audit_routes.py              # 审计日志
│   ├── sse_routes.py                # SSE 实时推送
│   ├── i18n_routes.py               # 国际化 API
│   ├── swagger_routes.py            # Swagger 文档
│   ├── apm_routes.py                # APM 监控
│   └── cleanup_routes.py            # 数据清理
│
├── auth/                            # 认证与安全
│   ├── jwt_handler.py               # JWT Token 生成/验证
│   ├── middleware.py                 # 登录验证装饰器
│   ├── quota_middleware.py           # 额度校验装饰器
│   ├── password.py                  # bcrypt 密码哈希
│   ├── user_model.py                # 用户数据模型
│   └── api_keys_config.py           # AES-256-GCM 密钥加密
│
├── scrapers/                        # 数据采集（15 个爬虫）
│   ├── coupang/                     # Coupang 爬虫组
│   ├── amazon/                      # Amazon 爬虫组 + SP-API
│   ├── keepa/                       # Keepa 历史数据
│   ├── naver/                       # Naver 趋势
│   ├── alibaba1688/                 # 1688 搜货
│   └── google_trends.py             # Google Trends
│
├── analysis/                        # AI 分析引擎
│   ├── ai_analysis/                 # AI 分析器组
│   │   ├── review_analyzer.py       # 评论分析
│   │   ├── detail_analyzer.py       # 详情页分析
│   │   └── risk_analyzer.py         # 风险雷达 + AI 总结
│   ├── profit_analysis/             # 利润分析
│   │   └── amazon_profit_calculator.py
│   ├── market_analysis/             # 市场分析
│   │   ├── category_analyzer.py     # 类目分析
│   │   └── report_generator.py      # 报告生成
│   ├── model_3d/                    # 3D 模块
│   │   ├── generator.py             # 3D 模型生成（TripoSR/Meshy）
│   │   └── video_renderer.py        # 视频渲染（FFmpeg）
│   ├── amazon_data_filter.py        # Amazon 数据筛选
│   └── data_filter.py               # 通用数据筛选
│
├── tasks/                           # Celery 异步任务
│   ├── scraping_tasks.py            # 抓取任务
│   ├── analysis_tasks.py            # 分析任务
│   └── threed_tasks.py              # 3D 生成 + 视频渲染任务
│
├── frontend/                        # Web 前端
│   ├── routes.py                    # 页面路由（16 个页面）
│   ├── templates/                   # Jinja2 模板
│   │   ├── base.html                # 基础布局（侧边栏 + 顶栏）
│   │   ├── auth.html                # 登录/注册
│   │   ├── dashboard.html           # 仪表盘
│   │   ├── new_project.html         # 新建项目
│   │   ├── project_detail.html      # 项目详情
│   │   ├── product_analysis.html    # 产品分析
│   │   ├── market_analysis.html     # 市场分析
│   │   ├── profit_calculator.html   # 利润计算
│   │   ├── report.html              # 决策报告
│   │   ├── threed_lab.html          # 3D 实验室
│   │   ├── subscription.html        # 订阅管理
│   │   ├── ai_settings.html         # AI 设置
│   │   ├── api_keys_settings.html   # API 密钥设置
│   │   ├── team.html                # 团队管理
│   │   ├── notifications.html       # 通知中心
│   │   └── apm_dashboard.html       # APM 监控面板
│   └── static/
│       ├── css/main.css             # 暗色主题 + 设计系统
│       └── js/api.js                # API 客户端 + 额度拦截
│
├── monetization/                    # 商业化
│   ├── subscription.py              # 三档订阅计划
│   └── affiliate.py                 # Affiliate 链接生成
│
├── chrome_extension/                # Chrome 扩展（Manifest V3）
│
├── database/                        # 数据库
│   ├── schema.sql                   # 建表 SQL（13+ 张表）
│   ├── connection.py                # 连接池管理
│   ├── init_db.py                   # 初始化 + 迁移
│   └── migrations/                  # 迁移脚本
│
├── i18n/                            # 多语言
│   └── locales/                     # zh_CN / en_US / ko_KR
│
├── tests/                           # 测试
│   ├── conftest.py                  # 测试配置
│   ├── test_all_modules.py          # 模块冒烟测试（20 项）
│   ├── test_api_integration.py      # API 集成测试（31 项）
│   ├── test_scrapers.py             # 爬虫模块 Mock 测试（26 项）
│   └── test_ai_analysis.py          # AI 分析模块 Mock 测试（25 项）
│
├── k8s/                             # Kubernetes 部署
│   ├── web.yaml                     # Web 服务 Deployment + Service
│   ├── worker.yaml                  # Celery Worker
│   ├── mysql.yaml                   # MySQL StatefulSet
│   ├── redis.yaml                   # Redis
│   ├── ingress.yaml                 # Ingress 路由
│   ├── configmap.yaml               # 配置
│   ├── hpa.yaml                     # 自动伸缩
│   └── monitoring.yaml              # Prometheus + Grafana
│
├── utils/                           # 工具模块
│   ├── apm_monitor.py               # APM 性能监控
│   ├── audit_logger.py              # 审计日志
│   ├── data_cleaner.py              # 数据清理
│   ├── data_exporter.py             # 数据导出
│   ├── email_sender.py              # 邮件发送
│   ├── error_handler.py             # 全局异常处理
│   ├── notification_manager.py      # 通知管理
│   ├── swagger_config.py            # OpenAPI 文档配置
│   └── task_notifier.py             # SSE 任务通知
│
└── docs/                            # 文档
    └── development_progress.md      # 开发进度
```

## 数据库

13+ 张核心数据表，覆盖完整数据链路：

| 表名 | 说明 |
|------|------|
| users | 用户账户 + 订阅信息 |
| keywords | 搜索关键词管理 |
| categories | 产品类目 |
| products | 产品基础信息 |
| product_images | 产品图片 |
| product_daily_stats | 每日运营数据 |
| reviews | 评论数据 |
| ai_review_analysis | AI 评论分析结果 |
| ai_detail_analysis | AI 详情页分析结果 |
| category_trends | 类目趋势数据 |
| source_products | 1688 货源信息 |
| profit_analysis | 利润分析结果 |
| selection_reports | 选品报告 |
| risk_assessments | 风险评估 |
| sourcing_projects | 选品项目 |
| assets_3d | 3D 模型资产 |
| analysis_tasks | 分析任务记录 |
| usage_records | 额度使用记录 |

## 订阅计划

| 功能 | Free（免费版） | Orbit（轨道版）$29.99/月 | Moonshot（登月版）$99.99/月 |
|------|:---:|:---:|:---:|
| 关键词搜索 | 5 次/天 | 50 次/天 | 无限制 |
| AI 分析 | 3 次/天 | 30 次/天 | 无限制 |
| 3D 模型生成 | - | 5 次/月 | 50 次/月 |
| 深度爬取 | - | ✓ | ✓ |
| 风险分析 | - | ✓ | ✓ |
| 1688 搜货 | - | ✓ | ✓ |
| 团队成员 | 1 | 3 | 10 |
| 数据保留 | 7 天 | 90 天 | 365 天 |

## 开发进度

- [x] 数据库 ER 关系设计与 SQL 脚本编写
- [x] 数据库连接层与 ORM 模型封装
- [x] 多语言国际化模块（中文/英文/韩文）
- [x] 通用工具模块（日志/HTTP 客户端/反爬虫）
- [x] Coupang 全套爬虫（搜索/详情/评论/后台）
- [x] Amazon 全套爬虫（搜索/详情/评论/深爬/SP-API/第三方 API）
- [x] Keepa 独立模块（BSR/价格/销量历史）
- [x] Naver 趋势 + Google Trends
- [x] 1688 以图搜货/关键词搜货
- [x] 数据筛选与 30 天转化率计算
- [x] AI 评论分析（卖点/痛点/画像）
- [x] AI 详情页分析（逻辑/视觉/信任）
- [x] AI 风险雷达（五维评估）
- [x] 利润计算（FBA/ROI/盈亏平衡/敏感性分析）
- [x] 类目趋势分析（GMV/垄断/新品占比）
- [x] 报告生成器（多语言 Markdown 报告）
- [x] 3D 模型生成（TripoSR/Meshy API 对接）
- [x] 3D 视频渲染（FFmpeg 运镜模板）
- [x] 主流程控制器（Coupang + Amazon Pipeline）
- [x] 命令行入口（交互式 + 参数式）
- [x] 用户认证系统（JWT + bcrypt）
- [x] API 密钥加密存储（AES-256-GCM）
- [x] 额度系统（配额校验 + 模块权限）
- [x] 订阅商业化（三档计划 + Affiliate）
- [x] Celery 异步任务队列
- [x] Chrome 扩展（Manifest V3 + WebSocket）
- [x] Docker 部署配置
- [x] Web 前端可视化界面（16 个页面）
- [x] REST API（23 个蓝图）
- [x] Dashboard 活动图表对接真实 API
- [x] 3D 模块数据库持久化（替换内存存储）
- [x] 额度中间件 Bug 修复（g.user_id + features 键映射）
- [x] API 集成测试（31 项）
- [x] CI/CD 配置（GitHub Actions）
- [x] 安全审计与修复
- [x] Stripe 支付集成（Checkout + Customer Portal + Webhook）
- [x] 邮箱验证 + 密码重置（SMTP）
- [x] OAuth 第三方登录（Google + GitHub）
- [x] 限流中间件（Flask-Limiter）
- [x] 全局异常处理器
- [x] 数据库连接池（DBUtils）
- [x] 操作审计日志
- [x] SSE 实时任务推送
- [x] 团队协作管理
- [x] 站内通知系统
- [x] 数据导出（CSV/Excel/PDF）
- [x] 数据清理工具
- [x] Swagger/OpenAPI 3.0 文档（105 个路径、115 个操作）
- [x] 国际化前端集成（data-i18n 属性）
- [x] 响应式 CSS（移动端适配）
- [x] K8s 部署配置（Deployment/Service/Ingress/HPA/PDB）
- [x] Prometheus + Grafana 监控
- [x] APM 性能监控面板
- [x] Mock 测试（爬虫 26 项 + AI 分析 25 项）

## 测试

```bash
# 运行模块冒烟测试（20 项）
python tests/test_all_modules.py

# 运行 API 集成测试（31 项）
python tests/test_api_integration.py

# 运行 Mock 测试（pytest）
python -m pytest tests/test_scrapers.py tests/test_ai_analysis.py -v
```

## 注意事项

1. **反爬虫**: 系统内置了随机延迟、UA 轮换、请求频率控制等反爬虫策略，请合理设置爬取速度
2. **API Key**: AI 分析功能需要配置 OpenAI API Key；Keepa/Naver 等需要对应 API Key
3. **Wing 后台**: 需要有 Coupang 卖家账号才能获取运营数据，无账号可跳过此步骤
4. **合规性**: 请遵守各平台的使用条款，合理使用爬虫功能
5. **安全**: 生产环境请务必修改 `JWT_SECRET_KEY` 和 `FLASK_SECRET_KEY`

## License

MIT License
