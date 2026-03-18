-- ============================================================
-- Coupang 跨境电商智能选品系统 - 完整数据库建表脚本
-- 数据库引擎: MySQL 8.0+
-- 字符集: utf8mb4 (支持韩文、中文、Emoji)
-- 更新时间: 2026-03-18
-- 包含所有表定义（基础表 + 迁移脚本中的表）
-- ============================================================

CREATE DATABASE IF NOT EXISTS coupang_selection
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE coupang_selection;

-- ============================================================
-- 0. 用户表 (users)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id                      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    username                VARCHAR(50)  NOT NULL UNIQUE COMMENT '用户名',
    email                   VARCHAR(120) NOT NULL UNIQUE COMMENT '邮箱',
    password_hash           VARCHAR(255) NOT NULL COMMENT 'bcrypt 密码哈希',
    nickname                VARCHAR(100) DEFAULT NULL COMMENT '昵称',
    role                    ENUM('user', 'admin', 'superadmin') DEFAULT 'user' COMMENT '角色',
    is_active               TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活',
    is_verified             TINYINT(1) NOT NULL DEFAULT 0 COMMENT '邮箱是否验证',
    language                VARCHAR(10) DEFAULT 'zh_CN' COMMENT '语言偏好',
    phone                   VARCHAR(30) DEFAULT NULL COMMENT '手机号',
    avatar_url              VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    openai_api_key          VARCHAR(255) DEFAULT NULL COMMENT 'OpenAI API Key (旧字段)',
    openai_model            VARCHAR(50) DEFAULT NULL COMMENT 'OpenAI 模型名 (旧字段)',
    ai_settings             JSON DEFAULT NULL COMMENT 'AI模型配置(JSON): provider, api_key, base_url, model, temperature 等',
    api_keys_settings       JSON DEFAULT NULL COMMENT '第三方 API 密钥配置 (AES-256-GCM 加密)',
    subscription_plan       VARCHAR(20) DEFAULT 'free' COMMENT '订阅计划: free/orbit/moonshot',
    subscription_started_at DATETIME DEFAULT NULL COMMENT '订阅开始时间',
    subscription_expires_at DATETIME DEFAULT NULL COMMENT '订阅到期时间',
    billing_cycle           VARCHAR(20) DEFAULT 'monthly' COMMENT '计费周期: monthly/yearly',
    last_login_at           DATETIME DEFAULT NULL COMMENT '最后登录时间',
    login_count             INT UNSIGNED DEFAULT 0 COMMENT '登录次数',
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_subscription (subscription_plan)
) ENGINE=InnoDB COMMENT='用户表';

-- ============================================================
-- 1. 搜索关键词表 (keywords)
-- ============================================================
CREATE TABLE IF NOT EXISTS keywords (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '关键词ID',
    keyword         VARCHAR(200) NOT NULL COMMENT '搜索关键词',
    platform        ENUM('coupang', 'amazon', 'naver', 'google') DEFAULT 'coupang' COMMENT '搜索平台',
    language        VARCHAR(10) DEFAULT 'ko' COMMENT '搜索语言',
    search_count    INT UNSIGNED DEFAULT 0 COMMENT '搜索次数',
    last_searched   DATETIME DEFAULT NULL COMMENT '最后搜索时间',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE INDEX idx_keyword_platform (keyword, platform),
    INDEX idx_last_searched (last_searched)
) ENGINE=InnoDB COMMENT='搜索关键词表';

-- ============================================================
-- 2. 商品分类表 (categories)
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '分类ID',
    platform        ENUM('coupang', 'amazon') DEFAULT 'coupang' COMMENT '平台',
    category_id     VARCHAR(50) NOT NULL COMMENT '平台分类ID',
    category_name   VARCHAR(200) NOT NULL COMMENT '分类名称',
    parent_id       INT UNSIGNED DEFAULT NULL COMMENT '父分类ID',
    level           TINYINT UNSIGNED DEFAULT 1 COMMENT '分类层级',
    product_count   INT UNSIGNED DEFAULT 0 COMMENT '商品数量',
    avg_price       DECIMAL(12,2) DEFAULT NULL COMMENT '平均价格',
    avg_rating      DECIMAL(3,2) DEFAULT NULL COMMENT '平均评分',
    competition     ENUM('low', 'medium', 'high', 'very_high') DEFAULT NULL COMMENT '竞争度',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_platform_category (platform, category_id),
    INDEX idx_parent (parent_id),
    INDEX idx_competition (competition)
) ENGINE=InnoDB COMMENT='商品分类表';

-- ============================================================
-- 3. 商品主表 (products)
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '商品ID',
    keyword_id      INT UNSIGNED DEFAULT NULL COMMENT '关联关键词ID',
    category_id     INT UNSIGNED DEFAULT NULL COMMENT '关联分类ID',
    platform        ENUM('coupang', 'amazon') DEFAULT 'coupang' COMMENT '平台',
    product_id      VARCHAR(50) NOT NULL COMMENT '平台商品ID (ASIN/Coupang ID)',
    product_name    VARCHAR(500) NOT NULL COMMENT '商品名称',
    brand           VARCHAR(200) DEFAULT NULL COMMENT '品牌',
    seller_name     VARCHAR(200) DEFAULT NULL COMMENT '卖家名称',
    price           DECIMAL(12,2) DEFAULT NULL COMMENT '当前价格',
    original_price  DECIMAL(12,2) DEFAULT NULL COMMENT '原价',
    currency        VARCHAR(5) DEFAULT 'KRW' COMMENT '货币',
    rating          DECIMAL(3,2) DEFAULT NULL COMMENT '评分',
    review_count    INT UNSIGNED DEFAULT 0 COMMENT '评论数',
    rank_position   INT UNSIGNED DEFAULT NULL COMMENT '搜索排名',
    bsr             INT UNSIGNED DEFAULT NULL COMMENT 'Best Seller Rank',
    est_sales_30d   INT UNSIGNED DEFAULT NULL COMMENT '预估月销量',
    fulfillment     VARCHAR(50) DEFAULT NULL COMMENT '配送方式 (FBA/FBM/Rocket)',
    is_rocket       TINYINT(1) DEFAULT 0 COMMENT '是否火箭配送',
    is_ad           TINYINT(1) DEFAULT 0 COMMENT '是否广告',
    product_url     VARCHAR(1000) DEFAULT NULL COMMENT '商品链接',
    image_url       VARCHAR(1000) DEFAULT NULL COMMENT '主图链接',
    detail_crawled  TINYINT(1) DEFAULT 0 COMMENT '是否已爬取详情',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_platform_product (platform, product_id),
    INDEX idx_keyword (keyword_id),
    INDEX idx_category (category_id),
    INDEX idx_price (price),
    INDEX idx_rating (rating),
    INDEX idx_review_count (review_count),
    INDEX idx_bsr (bsr)
) ENGINE=InnoDB COMMENT='商品主表';

-- ============================================================
-- 4. 每日指标表 (daily_metrics)
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_metrics (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '指标ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    metric_date     DATE NOT NULL COMMENT '指标日期',
    price           DECIMAL(12,2) DEFAULT NULL COMMENT '当日价格',
    rating          DECIMAL(3,2) DEFAULT NULL COMMENT '当日评分',
    review_count    INT UNSIGNED DEFAULT NULL COMMENT '当日评论数',
    rank_position   INT UNSIGNED DEFAULT NULL COMMENT '当日排名',
    bsr             INT UNSIGNED DEFAULT NULL COMMENT '当日BSR',
    est_sales       INT UNSIGNED DEFAULT NULL COMMENT '当日预估销量',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE INDEX idx_product_date (product_id, metric_date),
    INDEX idx_metric_date (metric_date)
) ENGINE=InnoDB COMMENT='每日指标表';

-- ============================================================
-- 5. 月度汇总表 (monthly_summary)
-- ============================================================
CREATE TABLE IF NOT EXISTS monthly_summary (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '汇总ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    summary_month   VARCHAR(7) NOT NULL COMMENT '汇总月份 (YYYY-MM)',
    avg_price       DECIMAL(12,2) DEFAULT NULL COMMENT '月均价格',
    min_price       DECIMAL(12,2) DEFAULT NULL COMMENT '月最低价',
    max_price       DECIMAL(12,2) DEFAULT NULL COMMENT '月最高价',
    avg_rating      DECIMAL(3,2) DEFAULT NULL COMMENT '月均评分',
    total_reviews   INT UNSIGNED DEFAULT 0 COMMENT '月新增评论数',
    avg_rank        INT UNSIGNED DEFAULT NULL COMMENT '月均排名',
    total_est_sales INT UNSIGNED DEFAULT 0 COMMENT '月预估总销量',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE INDEX idx_product_month (product_id, summary_month)
) ENGINE=InnoDB COMMENT='月度汇总表';

-- ============================================================
-- 6. 商品图片表 (product_images)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_images (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '图片ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    image_url       VARCHAR(1000) NOT NULL COMMENT '图片URL',
    image_type      ENUM('main', 'variant', 'detail', 'lifestyle') DEFAULT 'main' COMMENT '图片类型',
    local_path      VARCHAR(500) DEFAULT NULL COMMENT '本地存储路径',
    width           INT UNSIGNED DEFAULT NULL COMMENT '宽度(px)',
    height          INT UNSIGNED DEFAULT NULL COMMENT '高度(px)',
    file_size       INT UNSIGNED DEFAULT NULL COMMENT '文件大小(bytes)',
    sort_order      TINYINT UNSIGNED DEFAULT 0 COMMENT '排序',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_product (product_id),
    INDEX idx_type (image_type)
) ENGINE=InnoDB COMMENT='商品图片表';

-- ============================================================
-- 7. 商品评论表 (product_reviews)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_reviews (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '评论ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    review_id       VARCHAR(50) DEFAULT NULL COMMENT '平台评论ID',
    reviewer_name   VARCHAR(100) DEFAULT NULL COMMENT '评论者',
    rating          TINYINT UNSIGNED DEFAULT NULL COMMENT '评分(1-5)',
    title           VARCHAR(500) DEFAULT NULL COMMENT '评论标题',
    content         TEXT DEFAULT NULL COMMENT '评论内容',
    review_date     DATE DEFAULT NULL COMMENT '评论日期',
    verified        TINYINT(1) DEFAULT 0 COMMENT '是否验证购买',
    helpful_count   INT UNSIGNED DEFAULT 0 COMMENT '有用数',
    sentiment       ENUM('positive', 'neutral', 'negative') DEFAULT NULL COMMENT '情感倾向',
    language        VARCHAR(10) DEFAULT NULL COMMENT '评论语言',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_product (product_id),
    INDEX idx_rating (rating),
    INDEX idx_sentiment (sentiment),
    INDEX idx_review_date (review_date)
) ENGINE=InnoDB COMMENT='商品评论表';

-- ============================================================
-- 8. 评论分析结果表 (review_analysis)
-- ============================================================
CREATE TABLE IF NOT EXISTS review_analysis (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '分析ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    analysis_type   ENUM('sentiment', 'keyword', 'topic', 'competitor') DEFAULT 'sentiment' COMMENT '分析类型',
    positive_ratio  DECIMAL(5,2) DEFAULT NULL COMMENT '好评率(%)',
    negative_ratio  DECIMAL(5,2) DEFAULT NULL COMMENT '差评率(%)',
    neutral_ratio   DECIMAL(5,2) DEFAULT NULL COMMENT '中评率(%)',
    top_positive    JSON DEFAULT NULL COMMENT '主要好评关键词(JSON)',
    top_negative    JSON DEFAULT NULL COMMENT '主要差评关键词(JSON)',
    pain_points     JSON DEFAULT NULL COMMENT '用户痛点(JSON)',
    selling_points  JSON DEFAULT NULL COMMENT '卖点(JSON)',
    summary         TEXT DEFAULT NULL COMMENT 'AI分析摘要',
    total_analyzed  INT UNSIGNED DEFAULT 0 COMMENT '分析评论总数',
    analyzed_at     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',

    INDEX idx_product (product_id),
    INDEX idx_type (analysis_type)
) ENGINE=InnoDB COMMENT='评论分析结果表';

-- ============================================================
-- 9. 详情页分析表 (detail_page_analysis)
-- ============================================================
CREATE TABLE IF NOT EXISTS detail_page_analysis (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '分析ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    title_score     TINYINT UNSIGNED DEFAULT NULL COMMENT '标题评分(0-100)',
    image_count     TINYINT UNSIGNED DEFAULT NULL COMMENT '图片数量',
    image_quality   TINYINT UNSIGNED DEFAULT NULL COMMENT '图片质量评分(0-100)',
    bullet_count    TINYINT UNSIGNED DEFAULT NULL COMMENT 'Bullet Point数量',
    bullet_quality  TINYINT UNSIGNED DEFAULT NULL COMMENT 'Bullet质量评分(0-100)',
    description_len INT UNSIGNED DEFAULT NULL COMMENT '描述长度(字符)',
    has_video       TINYINT(1) DEFAULT 0 COMMENT '是否有视频',
    has_aplus       TINYINT(1) DEFAULT 0 COMMENT '是否有A+内容',
    has_brand_story TINYINT(1) DEFAULT 0 COMMENT '是否有品牌故事',
    listing_score   TINYINT UNSIGNED DEFAULT NULL COMMENT '综合Listing评分(0-100)',
    seo_keywords    JSON DEFAULT NULL COMMENT 'SEO关键词(JSON)',
    improvement     JSON DEFAULT NULL COMMENT '改进建议(JSON)',
    analyzed_at     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',

    INDEX idx_product (product_id),
    INDEX idx_listing_score (listing_score)
) ENGINE=InnoDB COMMENT='详情页分析表';

-- ============================================================
-- 10. 利润分析表 (profit_analysis)
-- ============================================================
CREATE TABLE IF NOT EXISTS profit_analysis (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '分析ID',
    product_id      INT UNSIGNED NOT NULL COMMENT '关联商品ID',
    selling_price   DECIMAL(12,2) DEFAULT NULL COMMENT '售价',
    cost_price      DECIMAL(12,2) DEFAULT NULL COMMENT '采购成本',
    shipping_cost   DECIMAL(12,2) DEFAULT NULL COMMENT '运费',
    platform_fee    DECIMAL(12,2) DEFAULT NULL COMMENT '平台佣金',
    fba_fee         DECIMAL(12,2) DEFAULT NULL COMMENT 'FBA费用',
    other_cost      DECIMAL(12,2) DEFAULT NULL COMMENT '其他成本',
    gross_profit    DECIMAL(12,2) DEFAULT NULL COMMENT '毛利润',
    profit_margin   DECIMAL(5,2) DEFAULT NULL COMMENT '利润率(%)',
    roi             DECIMAL(5,2) DEFAULT NULL COMMENT '投资回报率(%)',
    break_even_qty  INT UNSIGNED DEFAULT NULL COMMENT '盈亏平衡数量',
    currency        VARCHAR(5) DEFAULT 'KRW' COMMENT '货币',
    calculated_at   DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',

    INDEX idx_product (product_id),
    INDEX idx_profit_margin (profit_margin)
) ENGINE=InnoDB COMMENT='利润分析表';

-- ============================================================
-- 11. 趋势数据表 (trend_data)
-- ============================================================
CREATE TABLE IF NOT EXISTS trend_data (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '趋势ID',
    keyword         VARCHAR(200) NOT NULL COMMENT '关键词',
    platform        ENUM('google', 'naver', 'coupang') NOT NULL COMMENT '趋势平台',
    trend_date      DATE NOT NULL COMMENT '趋势日期',
    interest_value  INT UNSIGNED DEFAULT NULL COMMENT '搜索热度值(0-100)',
    region          VARCHAR(50) DEFAULT NULL COMMENT '地区',
    raw_data        JSON DEFAULT NULL COMMENT '原始趋势数据(JSON)',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_keyword_platform (keyword, platform),
    INDEX idx_trend_date (trend_date)
) ENGINE=InnoDB COMMENT='趋势数据表';

-- ============================================================
-- 12. 分析报告表 (analysis_reports)
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_reports (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '报告ID',
    keyword_id      INT UNSIGNED DEFAULT NULL COMMENT '关联关键词ID',
    report_type     ENUM('market', 'product', 'competitor', 'comprehensive') DEFAULT 'comprehensive' COMMENT '报告类型',
    title           VARCHAR(300) DEFAULT NULL COMMENT '报告标题',
    summary         TEXT DEFAULT NULL COMMENT '报告摘要',
    full_report     JSON DEFAULT NULL COMMENT '完整报告(JSON)',
    recommendation  ENUM('strong_buy', 'buy', 'hold', 'avoid') DEFAULT NULL COMMENT '推荐等级',
    confidence      DECIMAL(5,2) DEFAULT NULL COMMENT '置信度(%)',
    generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',

    INDEX idx_keyword (keyword_id),
    INDEX idx_type (report_type),
    INDEX idx_recommendation (recommendation)
) ENGINE=InnoDB COMMENT='分析报告表';

-- ============================================================
-- 13. 爬虫日志表 (crawl_logs)
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

-- ============================================================
-- 14. API 使用日志表 (api_usage_logs)
-- ============================================================
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    user_id         INT UNSIGNED NOT NULL COMMENT '用户ID',
    service_id      VARCHAR(50) NOT NULL COMMENT '服务ID (openai/keepa/naver 等)',
    endpoint        VARCHAR(255) DEFAULT NULL COMMENT '调用端点',
    tokens_used     INT UNSIGNED DEFAULT 0 COMMENT '消耗 Token 数',
    cost_usd        DECIMAL(10,6) DEFAULT 0 COMMENT '预估成本(USD)',
    status          ENUM('success', 'error', 'timeout') DEFAULT 'success' COMMENT '调用状态',
    error_message   TEXT DEFAULT NULL COMMENT '错误信息',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_user (user_id),
    INDEX idx_service (service_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='API 使用日志表';

-- ============================================================
-- 15. 配额使用记录表 (usage_records)
-- ============================================================
CREATE TABLE IF NOT EXISTS usage_records (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    action_type     VARCHAR(50) NOT NULL COMMENT '操作类型: scrape/analysis/report/3d',
    resource_id     VARCHAR(100) DEFAULT NULL COMMENT '关联资源ID',
    credits_used    INT DEFAULT 1 COMMENT '消耗额度',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_action (user_id, action_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='配额使用记录表';

-- ============================================================
-- 16. 订阅日志表 (subscription_logs)
-- ============================================================
CREATE TABLE IF NOT EXISTS subscription_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    action          VARCHAR(50) NOT NULL COMMENT '操作: subscribe/upgrade/downgrade/cancel/renew',
    plan_from       VARCHAR(20) DEFAULT NULL,
    plan_to         VARCHAR(20) DEFAULT NULL,
    amount          DECIMAL(10,2) DEFAULT NULL COMMENT '金额',
    currency        VARCHAR(5) DEFAULT 'USD',
    stripe_event_id VARCHAR(100) DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='订阅日志表';

-- ============================================================
-- 17. 返佣点击表 (affiliate_clicks)
-- ============================================================
CREATE TABLE IF NOT EXISTS affiliate_clicks (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED DEFAULT NULL,
    platform        VARCHAR(20) NOT NULL COMMENT '平台: amazon/coupang',
    product_id      VARCHAR(50) NOT NULL COMMENT '商品ID',
    affiliate_tag   VARCHAR(100) DEFAULT NULL,
    click_url       VARCHAR(1000) DEFAULT NULL,
    ip_address      VARCHAR(45) DEFAULT NULL,
    user_agent      VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_platform_product (platform, product_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='返佣点击表';

-- ============================================================
-- 18. 系统配置表 (system_config)
-- ============================================================
CREATE TABLE IF NOT EXISTS system_config (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    config_key      VARCHAR(100) NOT NULL UNIQUE,
    config_value    TEXT DEFAULT NULL,
    description     VARCHAR(255) DEFAULT NULL,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_key (config_key)
) ENGINE=InnoDB COMMENT='系统配置表';

-- ============================================================
-- 19. 选品项目表 (sourcing_projects)
-- ============================================================
CREATE TABLE IF NOT EXISTS sourcing_projects (
    id              VARCHAR(36) PRIMARY KEY COMMENT '项目UUID',
    user_id         INT UNSIGNED NOT NULL,
    name            VARCHAR(200) NOT NULL COMMENT '项目名称',
    keyword         VARCHAR(200) NOT NULL COMMENT '搜索关键词',
    marketplace     VARCHAR(20) DEFAULT 'US' COMMENT '市场: US/JP/DE/UK/KR',
    status          ENUM('created', 'scraping', 'analyzing', 'completed', 'failed') DEFAULT 'created',
    product_count   INT UNSIGNED DEFAULT 0,
    settings        JSON DEFAULT NULL COMMENT '项目配置',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='选品项目表';

-- ============================================================
-- 20. 项目产品表 (project_products)
-- ============================================================
CREATE TABLE IF NOT EXISTS project_products (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    project_id      VARCHAR(36) NOT NULL,
    asin            VARCHAR(20) NOT NULL COMMENT 'Amazon ASIN',
    title           VARCHAR(500) DEFAULT NULL,
    brand           VARCHAR(200) DEFAULT NULL,
    price           DECIMAL(12,2) DEFAULT NULL,
    currency        VARCHAR(5) DEFAULT 'USD',
    rating          DECIMAL(3,2) DEFAULT NULL,
    review_count    INT UNSIGNED DEFAULT 0,
    bsr             INT UNSIGNED DEFAULT NULL,
    category        VARCHAR(200) DEFAULT NULL,
    est_sales_30d   INT UNSIGNED DEFAULT NULL,
    fulfillment     VARCHAR(50) DEFAULT NULL,
    image_url       VARCHAR(1000) DEFAULT NULL,
    product_url     VARCHAR(1000) DEFAULT NULL,
    seller_count    INT UNSIGNED DEFAULT NULL,
    is_filtered     TINYINT(1) DEFAULT 0 COMMENT '是否被筛选掉',
    filter_reason   VARCHAR(200) DEFAULT NULL,
    raw_data        JSON DEFAULT NULL COMMENT '原始爬取数据',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_project (project_id),
    INDEX idx_asin (asin),
    INDEX idx_price (price),
    INDEX idx_bsr (bsr)
) ENGINE=InnoDB COMMENT='项目产品表';

-- ============================================================
-- 21. 分析任务表 (analysis_tasks)
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id              VARCHAR(36) PRIMARY KEY COMMENT '任务UUID',
    user_id         INT UNSIGNED NOT NULL,
    project_id      VARCHAR(36) DEFAULT NULL,
    task_type       ENUM('visual', 'review', 'market', 'report', 'scrape') NOT NULL,
    target_asin     VARCHAR(20) DEFAULT NULL,
    status          ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    progress        TINYINT UNSIGNED DEFAULT 0 COMMENT '进度(0-100)',
    result          JSON DEFAULT NULL COMMENT '分析结果',
    error_message   TEXT DEFAULT NULL,
    celery_task_id  VARCHAR(100) DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME DEFAULT NULL,

    INDEX idx_user (user_id),
    INDEX idx_project (project_id),
    INDEX idx_status (status),
    INDEX idx_type (task_type)
) ENGINE=InnoDB COMMENT='分析任务表';

-- ============================================================
-- 22. 3D 资产表 (assets_3d)
-- ============================================================
CREATE TABLE IF NOT EXISTS assets_3d (
    id              VARCHAR(36) PRIMARY KEY COMMENT '资产UUID',
    user_id         INT UNSIGNED NOT NULL,
    asin            VARCHAR(20) DEFAULT NULL,
    source_image    VARCHAR(1000) DEFAULT NULL COMMENT '源图片URL',
    model_url       VARCHAR(1000) DEFAULT NULL COMMENT '3D模型URL (GLB/OBJ)',
    thumbnail_url   VARCHAR(1000) DEFAULT NULL COMMENT '缩略图URL',
    video_url       VARCHAR(1000) DEFAULT NULL COMMENT '旋转视频URL',
    provider        VARCHAR(50) DEFAULT 'triposr' COMMENT '生成服务: triposr/meshy',
    status          ENUM('pending', 'generating', 'completed', 'failed') DEFAULT 'pending',
    metadata        JSON DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_asin (asin),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='3D 资产表';

-- ============================================================
-- 23. 利润计算记录表 (profit_calculations)
-- ============================================================
CREATE TABLE IF NOT EXISTS profit_calculations (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    asin            VARCHAR(20) DEFAULT NULL,
    product_name    VARCHAR(500) DEFAULT NULL,
    input_data      JSON NOT NULL COMMENT '输入参数',
    result_data     JSON NOT NULL COMMENT '计算结果',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_asin (asin),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='利润计算记录表';

-- ============================================================
-- 24. 审计日志表 (audit_logs)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED DEFAULT NULL,
    action          VARCHAR(100) NOT NULL COMMENT '操作类型',
    resource_type   VARCHAR(50) DEFAULT NULL COMMENT '资源类型',
    resource_id     VARCHAR(100) DEFAULT NULL COMMENT '资源ID',
    details         JSON DEFAULT NULL COMMENT '操作详情',
    ip_address      VARCHAR(45) DEFAULT NULL,
    user_agent      VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='审计日志表';

-- ============================================================
-- 25. OAuth 第三方登录表 (user_oauth)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_oauth (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    provider        VARCHAR(20) NOT NULL COMMENT '提供商: google/github',
    provider_uid    VARCHAR(255) NOT NULL COMMENT '第三方用户ID',
    access_token    VARCHAR(500) DEFAULT NULL,
    refresh_token   VARCHAR(500) DEFAULT NULL,
    profile_data    JSON DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_provider_uid (provider, provider_uid),
    INDEX idx_user (user_id)
) ENGINE=InnoDB COMMENT='OAuth 第三方登录表';

-- ============================================================
-- 26. 团队表 (teams)
-- ============================================================
CREATE TABLE IF NOT EXISTS teams (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    owner_id        INT UNSIGNED NOT NULL,
    description     TEXT DEFAULT NULL,
    max_members     INT UNSIGNED DEFAULT 5,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_owner (owner_id)
) ENGINE=InnoDB COMMENT='团队表';

-- ============================================================
-- 27. 团队成员表 (team_members)
-- ============================================================
CREATE TABLE IF NOT EXISTS team_members (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id         INT UNSIGNED NOT NULL,
    user_id         INT UNSIGNED NOT NULL,
    role            ENUM('owner', 'admin', 'member', 'viewer') DEFAULT 'member',
    joined_at       DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_team_user (team_id, user_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB COMMENT='团队成员表';

-- ============================================================
-- 28. 团队邀请表 (team_invitations)
-- ============================================================
CREATE TABLE IF NOT EXISTS team_invitations (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id         INT UNSIGNED NOT NULL,
    email           VARCHAR(120) NOT NULL,
    role            ENUM('admin', 'member', 'viewer') DEFAULT 'member',
    token           VARCHAR(100) NOT NULL UNIQUE,
    status          ENUM('pending', 'accepted', 'expired') DEFAULT 'pending',
    invited_by      INT UNSIGNED NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME NOT NULL,

    INDEX idx_team (team_id),
    INDEX idx_email (email),
    INDEX idx_token (token)
) ENGINE=InnoDB COMMENT='团队邀请表';

-- ============================================================
-- 29. 通知表 (notifications)
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    type            VARCHAR(50) NOT NULL COMMENT '通知类型: system/project/team/billing',
    title           VARCHAR(200) NOT NULL,
    message         TEXT DEFAULT NULL,
    is_read         TINYINT(1) DEFAULT 0,
    link            VARCHAR(500) DEFAULT NULL COMMENT '关联链接',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_read (user_id, is_read),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='通知表';

-- ============================================================
-- 30. 迁移记录表 (_migrations)
-- ============================================================
CREATE TABLE IF NOT EXISTS _migrations (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    filename        VARCHAR(255) NOT NULL UNIQUE,
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='数据库迁移记录表';
