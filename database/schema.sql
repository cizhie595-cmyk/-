-- ============================================================
-- Coupang 跨境电商智能选品系统 - 数据库建表脚本
-- 数据库引擎: MySQL 8.0+
-- 字符集: utf8mb4 (支持韩文、中文、Emoji)
-- 创建时间: 2026-03-17
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS coupang_selection
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE coupang_selection;

-- ============================================================
-- 1. 搜索关键词表 (keywords)
-- 记录每次选品调研使用的搜索关键词
-- ============================================================
CREATE TABLE IF NOT EXISTS keywords (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '关键词ID',
    word            VARCHAR(200) NOT NULL COMMENT '搜索关键词',
    top_n           INT UNSIGNED DEFAULT 50 COMMENT '抓取前N名产品',
    status          ENUM('pending', 'crawling', 'completed', 'failed') DEFAULT 'pending' COMMENT '抓取状态',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_word (word),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='搜索关键词表';

-- ============================================================
-- 2. 类目表 (categories)
-- 存储Coupang产品类目及类目级别的分析数据
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '类目ID',
    name                VARCHAR(200) NOT NULL COMMENT '类目名称',
    parent_id           INT UNSIGNED DEFAULT NULL COMMENT '父类目ID',
    commission_rate     DECIMAL(5,4) DEFAULT NULL COMMENT '平台佣金比例(如0.0800表示8%)',

    -- 趋势数据
    naver_trend_score   DECIMAL(10,2) DEFAULT NULL COMMENT 'Naver搜索趋势指数',
    coupang_trend_score DECIMAL(10,2) DEFAULT NULL COMMENT 'Coupang站内趋势指数',

    -- 体量预估
    monthly_gmv         DECIMAL(15,2) DEFAULT NULL COMMENT '月度GMV预估(KRW)',
    yearly_gmv          DECIMAL(15,2) DEFAULT NULL COMMENT '年度GMV预估(KRW)',

    -- 垄断程度
    top1_sales_ratio    DECIMAL(5,4) DEFAULT NULL COMMENT '前1名销量占比',
    top3_sales_ratio    DECIMAL(5,4) DEFAULT NULL COMMENT '前3名销量占比',
    top10_sales_ratio   DECIMAL(5,4) DEFAULT NULL COMMENT '前10名销量占比',

    -- 新品占比
    new_3m_ratio        DECIMAL(5,4) DEFAULT NULL COMMENT '近3个月上架新品占比',
    new_1y_ratio        DECIMAL(5,4) DEFAULT NULL COMMENT '近1年上架新品占比',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB COMMENT='产品类目表';

-- ============================================================
-- 3. 产品主表 (products)
-- 存储从Coupang前台抓取的产品基础信息
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '系统内部ID',
    coupang_product_id  VARCHAR(50) NOT NULL COMMENT 'Coupang产品ID',
    keyword_id          INT UNSIGNED DEFAULT NULL COMMENT '来源关键词ID',
    category_id         INT UNSIGNED DEFAULT NULL COMMENT '所属类目ID',
    ranking             INT UNSIGNED DEFAULT NULL COMMENT '搜索排名',

    -- 基础信息
    title               VARCHAR(500) NOT NULL COMMENT '产品标题',
    url                 VARCHAR(1000) NOT NULL COMMENT '产品链接',
    main_image_url      VARCHAR(1000) DEFAULT NULL COMMENT '主图URL',
    brand_name          VARCHAR(200) DEFAULT NULL COMMENT '品牌名',
    manufacturer        VARCHAR(200) DEFAULT NULL COMMENT '制造商',
    price               DECIMAL(12,2) DEFAULT NULL COMMENT '当前售价(KRW)',
    original_price      DECIMAL(12,2) DEFAULT NULL COMMENT '原价(KRW)',
    rating              DECIMAL(3,2) DEFAULT NULL COMMENT '商品评分(1-5)',
    review_count        INT UNSIGNED DEFAULT 0 COMMENT '总评论数',

    -- 配送方式
    delivery_type       ENUM('blue_rocket', 'orange_rocket', 'purple_rocket', 'self_delivery', 'unknown')
                        DEFAULT 'unknown' COMMENT '发货方式: 蓝火箭/橙火箭/紫火箭/自发货/未知',

    -- 筛选状态
    is_filtered         TINYINT(1) DEFAULT 0 COMMENT '是否被过滤(0=保留, 1=已过滤)',
    filter_reason       VARCHAR(500) DEFAULT NULL COMMENT '过滤原因',

    -- 推算上架时间
    estimated_listed_at DATE DEFAULT NULL COMMENT '推算上架时间(根据最早评论)',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_coupang_id (coupang_product_id),
    INDEX idx_keyword (keyword_id),
    INDEX idx_category (category_id),
    INDEX idx_ranking (ranking),
    INDEX idx_delivery (delivery_type),
    INDEX idx_filtered (is_filtered),
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='产品主表';

-- ============================================================
-- 4. 产品每日运营数据表 (daily_metrics)
-- 存储从卖家后台匹配获取的点击量、销量、曝光量等时序数据
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_metrics (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '产品ID(关联products表)',
    record_date     DATE NOT NULL COMMENT '数据日期',

    daily_clicks    INT UNSIGNED DEFAULT 0 COMMENT '当日点击量',
    daily_sales     INT UNSIGNED DEFAULT 0 COMMENT '当日销量',
    daily_views     INT UNSIGNED DEFAULT 0 COMMENT '当日曝光量',
    daily_revenue   DECIMAL(15,2) DEFAULT NULL COMMENT '当日销售额(KRW)',
    conversion_rate DECIMAL(8,6) DEFAULT NULL COMMENT '转化率(销量/点击量)',

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_product_date (product_id, record_date),
    INDEX idx_date (record_date),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='产品每日运营数据表';

-- ============================================================
-- 5. 30天汇总数据表 (monthly_summary)
-- 按30天窗口重新计算的汇总数据，用于筛选和排序
-- ============================================================
CREATE TABLE IF NOT EXISTS monthly_summary (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    product_id          INT UNSIGNED NOT NULL COMMENT '产品ID',
    summary_date        DATE NOT NULL COMMENT '汇总截止日期',

    total_clicks_30d    INT UNSIGNED DEFAULT 0 COMMENT '近30天总点击量',
    total_sales_30d     INT UNSIGNED DEFAULT 0 COMMENT '近30天总销量',
    total_views_30d     INT UNSIGNED DEFAULT 0 COMMENT '近30天总曝光量',
    total_revenue_30d   DECIMAL(15,2) DEFAULT NULL COMMENT '近30天总销售额(KRW)',
    avg_conversion_rate DECIMAL(8,6) DEFAULT NULL COMMENT '近30天平均转化率',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_product_summary (product_id, summary_date),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='30天汇总数据表';

-- ============================================================
-- 6. 产品图片表 (product_images)
-- 存储主图、SKU图、详情页截图等
-- ============================================================
CREATE TABLE IF NOT EXISTS product_images (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '图片ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '产品ID',
    image_type      ENUM('main', 'sku', 'detail', 'other') DEFAULT 'main' COMMENT '图片类型: 主图/SKU图/详情页/其他',
    image_url       VARCHAR(1000) NOT NULL COMMENT '原始图片URL',
    local_path      VARCHAR(500) DEFAULT NULL COMMENT '本地存储路径',
    sort_order      INT UNSIGNED DEFAULT 0 COMMENT '排序序号',

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_product (product_id),
    INDEX idx_type (image_type),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='产品图片表';

-- ============================================================
-- 7. 产品评论表 (product_reviews)
-- 存储每个产品的所有评论数据
-- ============================================================
CREATE TABLE IF NOT EXISTS product_reviews (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '评论ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '产品ID',

    author          VARCHAR(200) DEFAULT NULL COMMENT '评论者昵称',
    rating          TINYINT UNSIGNED DEFAULT NULL COMMENT '评分(1-5)',
    content         TEXT DEFAULT NULL COMMENT '评论内容',
    sku_attribute   VARCHAR(300) DEFAULT NULL COMMENT 'SKU属性(如颜色/规格)',
    review_date     DATETIME DEFAULT NULL COMMENT '评论时间',

    -- 刷单检测
    is_suspicious   TINYINT(1) DEFAULT 0 COMMENT '是否疑似刷单(0=正常, 1=疑似)',
    suspicious_reason VARCHAR(300) DEFAULT NULL COMMENT '疑似刷单原因',

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_product (product_id),
    INDEX idx_rating (rating),
    INDEX idx_suspicious (is_suspicious),
    INDEX idx_review_date (review_date),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='产品评论表';

-- ============================================================
-- 8. 评论分析汇总表 (review_analysis)
-- 存储对评论进行AI分析后的汇总结果
-- ============================================================
CREATE TABLE IF NOT EXISTS review_analysis (
    id                      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '分析ID',
    product_id              INT UNSIGNED NOT NULL COMMENT '产品ID',

    total_reviews           INT UNSIGNED DEFAULT 0 COMMENT '总评论数(去除刷单后)',
    avg_rating              DECIMAL(3,2) DEFAULT NULL COMMENT '平均评分',
    rating_1_count          INT UNSIGNED DEFAULT 0 COMMENT '1星评论数',
    rating_2_count          INT UNSIGNED DEFAULT 0 COMMENT '2星评论数',
    rating_3_count          INT UNSIGNED DEFAULT 0 COMMENT '3星评论数',
    rating_4_count          INT UNSIGNED DEFAULT 0 COMMENT '4星评论数',
    rating_5_count          INT UNSIGNED DEFAULT 0 COMMENT '5星评论数',

    -- AI提取的结构化信息
    selling_points          JSON DEFAULT NULL COMMENT '卖点提取(JSON数组)',
    pain_points             JSON DEFAULT NULL COMMENT '痛点提取(JSON数组)',
    audience_profile        JSON DEFAULT NULL COMMENT '人群画像(JSON对象)',
    sku_sales_distribution  JSON DEFAULT NULL COMMENT '各SKU属性销量占比(JSON对象)',
    earliest_review_date    DATE DEFAULT NULL COMMENT '最早评论时间(推算上架时间)',

    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='评论分析汇总表';

-- ============================================================
-- 9. 详情页AI分析表 (detail_page_analysis)
-- 存储详情页的逻辑结构、文本语义、信任锚点、视觉语义分析
-- ============================================================
CREATE TABLE IF NOT EXISTS detail_page_analysis (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '分析ID',
    product_id          INT UNSIGNED NOT NULL COMMENT '产品ID',

    -- 逻辑结构分析 (Logic Flow)
    logic_structure     JSON DEFAULT NULL COMMENT '逻辑结构: 痛点引入/原理拆解/竞品对比/信任背书/限时促销',
    conversion_model    VARCHAR(100) DEFAULT NULL COMMENT '转化模型(如AIDA)',

    -- 文本语义分析 (Visual SEO & Copy)
    extracted_text      TEXT DEFAULT NULL COMMENT 'OCR提取的文案全文',
    keyword_frequency   JSON DEFAULT NULL COMMENT '关键词频次(JSON对象)',
    tone_analysis       VARCHAR(100) DEFAULT NULL COMMENT '语气分析: 感性引导/理性技术',
    usp_points          JSON DEFAULT NULL COMMENT '核心卖点USP(JSON数组)',

    -- 信任锚点分析 (Trust Signals)
    trust_signals       JSON DEFAULT NULL COMMENT '信任锚点: 认证图标/检测报告/明星背书/真实场景',
    compliance_required JSON DEFAULT NULL COMMENT '所需行业资质(JSON数组)',

    -- 视觉语义分析 (Visual Semantics)
    color_analysis      JSON DEFAULT NULL COMMENT '色彩心理学分析(JSON对象)',
    font_hierarchy      VARCHAR(300) DEFAULT NULL COMMENT '字体层级描述',
    model_localization  VARCHAR(100) DEFAULT NULL COMMENT '模特本土化程度',
    brand_positioning   ENUM('budget', 'mid_range', 'premium', 'unknown')
                        DEFAULT 'unknown' COMMENT '品牌定位: 性价比/中端/高端/未知',

    -- 产品特性分析维度
    product_attributes  JSON DEFAULT NULL COMMENT '产品特性分析(如续航/规格/颜色等, JSON对象)',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='详情页AI分析表';

-- ============================================================
-- 10. 利润分析表 (profit_analysis)
-- 存储每个产品的成本、费用与利润计算结果
-- ============================================================
CREATE TABLE IF NOT EXISTS profit_analysis (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '利润分析ID',
    product_id          INT UNSIGNED NOT NULL COMMENT '产品ID',

    -- 1688货源信息
    source_1688_url     VARCHAR(1000) DEFAULT NULL COMMENT '1688货源链接',
    source_1688_title   VARCHAR(500) DEFAULT NULL COMMENT '1688货源标题',
    source_cost_rmb     DECIMAL(10,2) DEFAULT NULL COMMENT '采购成本(RMB)',
    freight_cost_rmb    DECIMAL(10,2) DEFAULT NULL COMMENT '头程运费(RMB/件)',

    -- Coupang平台费用
    commission_rate     DECIMAL(5,4) DEFAULT NULL COMMENT '平台佣金比例',
    delivery_fee_krw    DECIMAL(10,2) DEFAULT NULL COMMENT 'Coupang配送费(KRW)',
    other_fee_krw       DECIMAL(10,2) DEFAULT 0 COMMENT '其他费用(KRW)',

    -- 汇率与计算结果
    exchange_rate       DECIMAL(10,4) DEFAULT NULL COMMENT '计算时RMB->KRW汇率',
    selling_price_krw   DECIMAL(12,2) DEFAULT NULL COMMENT '售价(KRW)',
    total_cost_krw      DECIMAL(12,2) DEFAULT NULL COMMENT '总成本(KRW)',
    estimated_profit    DECIMAL(12,2) DEFAULT NULL COMMENT '预估单件利润(KRW)',
    profit_margin       DECIMAL(8,6) DEFAULT NULL COMMENT '利润率',
    roi                 DECIMAL(8,4) DEFAULT NULL COMMENT '投资回报率(ROI)',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='利润分析表';

-- ============================================================
-- 11. 趋势数据表 (trend_data)
-- 存储Naver和Coupang的趋势时序数据
-- ============================================================
CREATE TABLE IF NOT EXISTS trend_data (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    keyword_id      INT UNSIGNED NOT NULL COMMENT '关键词ID',
    source          ENUM('naver', 'coupang') NOT NULL COMMENT '数据来源',
    record_date     DATE NOT NULL COMMENT '数据日期',
    trend_value     DECIMAL(10,2) DEFAULT NULL COMMENT '趋势指数值',

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_keyword_source_date (keyword_id, source, record_date),
    INDEX idx_source (source),
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='趋势数据表';

-- ============================================================
-- 12. 分析报告表 (analysis_reports)
-- 存储最终的市场分析总结与风险分析报告
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_reports (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '报告ID',
    keyword_id          INT UNSIGNED DEFAULT NULL COMMENT '关联关键词ID',
    report_type         ENUM('market_summary', 'opportunity', 'risk') NOT NULL COMMENT '报告类型: 市场总结/机会分析/风险分析',
    title               VARCHAR(300) DEFAULT NULL COMMENT '报告标题',
    content             LONGTEXT DEFAULT NULL COMMENT '报告正文(Markdown格式)',
    ai_model            VARCHAR(100) DEFAULT NULL COMMENT '生成所用AI模型',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_keyword (keyword_id),
    INDEX idx_type (report_type),
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='分析报告表';

-- ============================================================
-- 13. 爬虫任务日志表 (crawl_logs)
-- 记录每次爬虫任务的执行状态与日志
-- ============================================================
CREATE TABLE IF NOT EXISTS crawl_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    task_type       ENUM('keyword_search', 'backend_match', 'detail_crawl', 'review_crawl', 'image_download', 'trend_crawl', 'source_search')
                    NOT NULL COMMENT '任务类型',
    target_id       INT UNSIGNED DEFAULT NULL COMMENT '目标ID(产品ID或关键词ID)',
    status          ENUM('running', 'success', 'failed', 'retry') DEFAULT 'running' COMMENT '执行状态',
    message         TEXT DEFAULT NULL COMMENT '日志信息',
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    finished_at     DATETIME DEFAULT NULL COMMENT '完成时间',

    INDEX idx_task_type (task_type),
    INDEX idx_status (status),
    INDEX idx_started (started_at)
) ENGINE=InnoDB COMMENT='爬虫任务日志表';
