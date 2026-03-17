# Coupang 跨境电商智能选品系统

> Coupang Cross-border Product Selection System / 쿠팡 크로스보더 상품 선정 시스템

## 系统概述

本系统是一套面向 Coupang（韩国酷澎）跨境电商卖家的**智能选品分析工具**，覆盖从数据采集、筛选、AI分析到利润核算的完整选品流程。

支持 **中文 / English / 한국어** 三种语言。

## 功能架构

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (命令行入口)                    │
│                    pipeline.py (主流程控制器)              │
├─────────────────────────────────────────────────────────┤
│  scrapers/                    │  analysis/                │
│  ├── coupang/                 │  ├── data_filter.py       │
│  │   ├── search_crawler.py    │  ├── ai_analysis/         │
│  │   ├── detail_crawler.py    │  │   ├── review_analyzer  │
│  │   ├── review_crawler.py    │  │   └── detail_analyzer  │
│  │   └── backend_crawler.py   │  ├── profit_analysis/     │
│  └── alibaba1688/             │  │   └── profit_calculator│
│      └── source_crawler.py    │  └── market_analysis/     │
│                               │      ├── category_analyzer│
│                               │      └── report_generator │
├─────────────────────────────────────────────────────────┤
│  database/          │  config/       │  i18n/             │
│  ├── schema.sql     │  └── database  │  ├── zh_CN.json    │
│  ├── connection.py  │     .py        │  ├── en_US.json    │
│  ├── models.py      │                │  └── ko_KR.json    │
│  └── init_db.py     │                │                    │
└─────────────────────────────────────────────────────────┘
```

## 10步选品流程

| 步骤 | 模块 | 功能说明 |
|------|------|---------|
| Step 1 | 搜索爬虫 | 输入韩文关键词，爬取Coupang搜索结果列表 |
| Step 2 | 后台匹配 | 登录Wing后台，匹配产品获取点击量/销量/曝光量 |
| Step 3 | 数据筛选 | 规则筛选 + AI智能筛选，过滤不相关/低质量产品 |
| Step 4 | 详情爬取 | 爬取产品详情页（图片、规格、配送方式） |
| Step 5 | 评论分析 | 爬取评论 → AI提取卖点/痛点/人群画像 |
| Step 6 | 详情分析 | AI分析详情页逻辑结构/视觉语义/信任锚点 |
| Step 7 | 趋势分析 | Naver搜索趋势 + GMV预估 + 垄断程度 + 新品占比 |
| Step 8 | 货源搜索 | 1688以图搜货/关键词搜货，确定采购成本 |
| Step 9 | 利润计算 | 核算利润率/ROI/盈亏平衡价 + 敏感性分析 |
| Step 10 | 报告生成 | 输出完整Markdown分析报告 |

## 快速开始

### 1. 环境要求

- Python 3.10+
- MySQL 8.0+（可选，用于数据持久化）

### 2. 安装依赖

```bash
git clone https://github.com/cizhie595-cmyk/-.git
cd -

pip install -r requirements.txt

# 安装浏览器驱动（评论爬取可能需要）
playwright install chromium
```

### 3. 配置

```bash
# 复制配置文件
cp .env.example .env
cp config.example.json config.json

# 编辑 .env 填入数据库信息
# 编辑 config.json 填入 API Key 等
```

### 4. 初始化数据库（可选）

```bash
python database/init_db.py
```

### 5. 运行

```bash
# 基础模式（快速体验）
python main.py --keyword "무선 이어폰" --skip-backend --skip-1688 --lang zh_CN

# 完整模式
python main.py --keyword "보조배터리" \
  --wing-user your@email.com --wing-pass yourpass \
  --lang zh_CN --save-raw

# 交互式模式（无参数启动）
python main.py

# 使用配置文件
python main.py --keyword "텀블러" --config config.json
```

## 命令行参数

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|--------|
| `--keyword` | `-k` | 搜索关键词（韩文） | 必填 |
| `--lang` | `-l` | 输出语言 (zh_CN/en_US/ko_KR) | zh_CN |
| `--max-products` | `-m` | 最大产品数 | 50 |
| `--skip-backend` | | 跳过Wing后台数据 | False |
| `--skip-1688` | | 跳过1688货源搜索 | False |
| `--wing-user` | | Wing后台账号 | None |
| `--wing-pass` | | Wing后台密码 | None |
| `--openai-key` | | OpenAI API Key | 环境变量 |
| `--output-dir` | `-o` | 报告输出目录 | reports |
| `--save-raw` | | 保存原始数据JSON | False |
| `--config` | `-c` | JSON配置文件路径 | None |
| `--exchange-rate` | | 人民币对韩元汇率 | 190.0 |
| `--freight-per-kg` | | 头程运费(RMB/kg) | 15.0 |
| `--commission-rate` | | 平台佣金比例 | 0.10 |

## 项目结构

```
coupang-product-selection/
├── main.py                          # 命令行入口
├── pipeline.py                      # 主流程控制器
├── config.example.json              # 配置文件模板
├── requirements.txt                 # Python 依赖
├── .env.example                     # 环境变量模板
├── .gitignore
│
├── scrapers/                        # 爬虫模块
│   ├── coupang/
│   │   ├── search_crawler.py        # 搜索列表爬虫
│   │   ├── detail_crawler.py        # 详情页爬虫
│   │   ├── review_crawler.py        # 评论爬虫（含刷单检测）
│   │   └── backend_crawler.py       # Wing后台数据爬虫
│   └── alibaba1688/
│       └── source_crawler.py        # 1688以图搜货/关键词搜货
│
├── analysis/                        # 分析模块
│   ├── data_filter.py               # 数据筛选（规则+AI）
│   ├── ai_analysis/
│   │   ├── review_analyzer.py       # AI评论分析（卖点/痛点/画像）
│   │   └── detail_analyzer.py       # AI详情页分析（逻辑/视觉/信任）
│   ├── profit_analysis/
│   │   └── profit_calculator.py     # 利润计算（ROI/盈亏平衡/敏感性）
│   └── market_analysis/
│       ├── category_analyzer.py     # 类目趋势分析
│       └── report_generator.py      # 报告生成器
│
├── database/                        # 数据库
│   ├── schema.sql                   # 建表SQL（13张表）
│   ├── init_db.py                   # 一键初始化脚本
│   ├── connection.py                # 连接池管理
│   ├── models.py                    # 数据模型(ORM)
│   └── seeds/
│       └── sample_data.sql          # 示例数据
│
├── config/                          # 配置
│   └── database.py                  # 数据库配置
│
├── i18n/                            # 多语言
│   ├── __init__.py                  # i18n引擎
│   └── locales/
│       ├── zh_CN.json               # 中文
│       ├── en_US.json               # English
│       └── ko_KR.json               # 한국어
│
├── utils/                           # 工具
│   ├── logger.py                    # 日志（多语言）
│   └── http_client.py              # HTTP请求（反爬虫）
│
├── data/                            # 数据目录（运行时生成）
│   └── images/                      # 下载的产品图片
│
└── reports/                         # 报告目录（运行时生成）
    └── report_*.md                  # 分析报告
```

## 核心模块说明

### 爬虫模块 (scrapers/)

- **搜索爬虫**: 模拟浏览器访问Coupang搜索页，提取产品列表（标题、价格、评分、链接等）
- **详情爬虫**: 爬取产品详情页，提取完整信息（图片、规格、配送方式、SKU选项等）
- **评论爬虫**: 支持AJAX API和HTML两种方式爬取评论，内置刷单检测算法
- **后台爬虫**: 模拟登录Coupang Wing卖家后台，获取点击量/销量/曝光量等运营数据
- **1688爬虫**: 支持以图搜货和关键词搜货，提取价格/起订量/供应商信息

### AI分析模块 (analysis/)

- **评论分析**: 使用GPT提取卖点/痛点/人群画像/改进建议
- **详情页分析**: 使用GPT Vision分析页面逻辑结构/文案语义/信任锚点/视觉设计
- **数据筛选**: 规则筛选 + AI相关性判断双重过滤
- **利润计算**: 完整成本核算（采购+运费+佣金+VAT），支持敏感性分析
- **类目分析**: Naver趋势 + GMV预估 + 垄断程度 + 新品占比

### 数据库 (database/)

13张核心数据表，覆盖完整数据链路：

| 表名 | 说明 |
|------|------|
| keywords | 搜索关键词管理 |
| categories | 产品类目 |
| products | 产品基础信息 |
| product_images | 产品图片 |
| product_daily_stats | 每日运营数据 |
| reviews | 评论数据 |
| ai_review_analysis | AI评论分析结果 |
| ai_detail_analysis | AI详情页分析结果 |
| category_trends | 类目趋势数据 |
| source_products | 1688货源信息 |
| profit_analysis | 利润分析结果 |
| selection_reports | 选品报告 |
| risk_assessments | 风险评估 |

## 开发进度

- [x] 数据库 ER 关系设计与 SQL 脚本编写
- [x] 数据库连接层与 ORM 模型封装
- [x] 多语言国际化模块（中文/英文/韩文）
- [x] 通用工具模块（日志/HTTP客户端/反爬虫）
- [x] Coupang 前台搜索列表爬虫
- [x] Coupang 产品详情页爬虫
- [x] Coupang 评论爬虫（含刷单检测）
- [x] Coupang Wing 后台数据爬虫
- [x] 数据筛选与30天转化率计算
- [x] AI 评论分析（卖点/痛点/画像）
- [x] AI 详情页分析（逻辑/视觉/信任）
- [x] 1688 以图搜货/关键词搜货
- [x] 利润计算（ROI/盈亏平衡/敏感性分析）
- [x] 类目趋势分析（GMV/垄断/新品占比）
- [x] 报告生成器（多语言Markdown报告）
- [x] 主流程控制器（Pipeline）
- [x] 命令行入口（交互式+参数式）
- [ ] 前端可视化界面

## 注意事项

1. **反爬虫**: 系统内置了随机延迟、UA轮换、请求频率控制等反爬虫策略，请合理设置爬取速度
2. **API Key**: AI分析功能需要配置 OpenAI API Key；Naver趋势需要 Naver API Key
3. **Wing后台**: 需要有Coupang卖家账号才能获取运营数据，无账号可跳过此步骤
4. **合规性**: 请遵守各平台的使用条款，合理使用爬虫功能

## License

MIT License
