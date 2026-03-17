-- ============================================================
-- 迁移脚本 004: 选品项目、分析任务、3D 资产表
-- 对应 PRD 6.1 Product, 6.2 Analysis_Report, 6.3 Asset_3D
-- 执行方式: mysql -u root -p coupang_selection < database/migrations/004_add_projects_and_assets.sql
-- ============================================================

-- 1. 选品项目表
CREATE TABLE IF NOT EXISTS sourcing_projects (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '项目ID',
    user_id             INT UNSIGNED NOT NULL COMMENT '所属用户ID',
    name                VARCHAR(200) NOT NULL COMMENT '项目名称',
    marketplace_id      VARCHAR(50) DEFAULT 'ATVPDKIKX0DER' COMMENT '站点ID (如 ATVPDKIKX0DER=US)',
    keyword             VARCHAR(200) DEFAULT NULL COMMENT '搜索关键词',
    file_upload_id      VARCHAR(100) DEFAULT NULL COMMENT '上传文件ID (Search Term Report)',
    scrape_depth        INT UNSIGNED DEFAULT 100 COMMENT '抓取深度 (50/100/200)',
    status              ENUM('created', 'scraping', 'scraped', 'filtering', 'analyzing', 'completed', 'failed')
                        DEFAULT 'created' COMMENT '项目状态',
    product_count       INT UNSIGNED DEFAULT 0 COMMENT '抓取到的产品数量',
    filtered_count      INT UNSIGNED DEFAULT 0 COMMENT '筛选后保留的产品数量',
    error_message       TEXT DEFAULT NULL COMMENT '错误信息',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选品项目表';

-- 2. 项目产品关联表 (存储抓取回来的产品数据)
CREATE TABLE IF NOT EXISTS project_products (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    project_id          INT UNSIGNED NOT NULL COMMENT '所属项目ID',
    asin                VARCHAR(20) DEFAULT NULL COMMENT 'Amazon ASIN',
    marketplace_id      VARCHAR(50) DEFAULT NULL COMMENT '站点ID',
    title               VARCHAR(500) NOT NULL COMMENT '商品标题',
    brand               VARCHAR(200) DEFAULT NULL COMMENT '品牌名称',
    main_image_url      VARCHAR(1000) DEFAULT NULL COMMENT '主图URL',
    price_current       DECIMAL(10,2) DEFAULT NULL COMMENT '当前售价',
    fulfillment_type    ENUM('FBA', 'FBM', 'SFP', 'unknown') DEFAULT 'unknown' COMMENT '发货方式',
    rating              DECIMAL(3,2) DEFAULT NULL COMMENT '星级评分',
    review_count        INT UNSIGNED DEFAULT 0 COMMENT '评论数',
    est_sales_30d       INT UNSIGNED DEFAULT NULL COMMENT '30天预估销量',
    cvr_30d             DECIMAL(5,2) DEFAULT NULL COMMENT '30天预估转化率(%)',
    bsr_rank            INT UNSIGNED DEFAULT NULL COMMENT 'BSR排名',
    bsr_category        VARCHAR(200) DEFAULT NULL COMMENT 'BSR所属类目',
    is_filtered         TINYINT(1) DEFAULT 0 COMMENT '是否被过滤',
    filter_reason       VARCHAR(500) DEFAULT NULL COMMENT '过滤原因',
    raw_data            JSON DEFAULT NULL COMMENT '原始抓取数据(JSON)',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_project (project_id),
    INDEX idx_asin (asin),
    FOREIGN KEY (project_id) REFERENCES sourcing_projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='项目产品关联表';

-- 3. 分析任务表 (对应 PRD 6.2 Analysis_Report)
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
    task_type           ENUM('visual', 'reviews', 'report') NOT NULL COMMENT '任务类型',
    user_id             INT UNSIGNED NOT NULL COMMENT '所属用户ID',
    project_id          INT UNSIGNED DEFAULT NULL COMMENT '关联项目ID',
    product_id          INT UNSIGNED DEFAULT NULL COMMENT '关联产品ID',
    asin                VARCHAR(20) DEFAULT NULL COMMENT 'ASIN',
    status              ENUM('pending', 'processing', 'completed', 'failed')
                        DEFAULT 'pending' COMMENT '任务状态',
    -- 分析参数
    dimensions          JSON DEFAULT NULL COMMENT '分析维度 (视觉分析用)',
    review_count        INT UNSIGNED DEFAULT 500 COMMENT '评论数量 (评论分析用)',
    -- 分析结果
    visual_usps         JSON DEFAULT NULL COMMENT 'AI提取的视觉核心卖点',
    trust_signals       JSON DEFAULT NULL COMMENT 'AI识别的信任背书',
    pain_points         JSON DEFAULT NULL COMMENT '差评痛点及权重',
    buyer_persona       TEXT DEFAULT NULL COMMENT 'AI描绘的目标人群画像',
    risk_score          INT UNSIGNED DEFAULT NULL COMMENT '综合风险评分(1-100)',
    report_url          VARCHAR(500) DEFAULT NULL COMMENT '报告文件URL',
    result_data         JSON DEFAULT NULL COMMENT '完整分析结果(JSON)',
    error_message       TEXT DEFAULT NULL COMMENT '错误信息',
    started_at          DATETIME DEFAULT NULL COMMENT '开始处理时间',
    completed_at        DATETIME DEFAULT NULL COMMENT '完成时间',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_project (project_id),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析任务表';

-- 4. 3D 资产表 (对应 PRD 6.3 Asset_3D)
CREATE TABLE IF NOT EXISTS assets_3d (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '资产ID',
    user_id             INT UNSIGNED NOT NULL COMMENT '所属用户ID',
    product_id          INT UNSIGNED DEFAULT NULL COMMENT '关联产品ID',
    asin                VARCHAR(20) DEFAULT NULL COMMENT '关联ASIN',
    -- Meshy API 相关
    meshy_task_id       VARCHAR(100) DEFAULT NULL COMMENT 'Meshy API任务ID',
    status              ENUM('pending', 'processing', 'completed', 'failed')
                        DEFAULT 'pending' COMMENT '任务状态',
    progress_pct        INT UNSIGNED DEFAULT 0 COMMENT '生成进度百分比(0-100)',
    -- 输入
    source_image_urls   JSON DEFAULT NULL COMMENT '源图片URL列表(1-3张)',
    -- 输出
    glb_file_url        VARCHAR(500) DEFAULT NULL COMMENT 'GLB模型文件URL',
    thumbnail_url       VARCHAR(500) DEFAULT NULL COMMENT '缩略图URL',
    -- 视频渲染
    render_task_id      VARCHAR(100) DEFAULT NULL COMMENT '视频渲染任务ID',
    render_status       ENUM('none', 'pending', 'rendering', 'completed', 'failed')
                        DEFAULT 'none' COMMENT '视频渲染状态',
    render_template     VARCHAR(50) DEFAULT NULL COMMENT '运镜模板(turntable/zoom/orbit)',
    render_resolution   VARCHAR(20) DEFAULT NULL COMMENT '渲染分辨率(720p/1080p/4k)',
    video_url           VARCHAR(500) DEFAULT NULL COMMENT '渲染视频URL',
    -- 元数据
    error_message       TEXT DEFAULT NULL COMMENT '错误信息',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_meshy_task (meshy_task_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='3D资产表';

-- 5. 利润计算记录表
CREATE TABLE IF NOT EXISTS profit_calculations (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             INT UNSIGNED NOT NULL,
    product_id          INT UNSIGNED DEFAULT NULL,
    asin                VARCHAR(20) DEFAULT NULL,
    -- 输入参数
    selling_price       DECIMAL(10,2) NOT NULL COMMENT '售价',
    sourcing_cost       DECIMAL(10,2) NOT NULL COMMENT '采购成本',
    shipping_cost_per_kg DECIMAL(10,2) DEFAULT 0 COMMENT '头程运费/kg',
    estimated_cpa       DECIMAL(10,2) DEFAULT 0 COMMENT '预估CPA',
    return_rate         DECIMAL(5,4) DEFAULT 0.05 COMMENT '退货率',
    -- 计算结果
    landed_cost         DECIMAL(10,2) DEFAULT NULL COMMENT '落地成本',
    amazon_fees         DECIMAL(10,2) DEFAULT NULL COMMENT '亚马逊费用',
    net_profit          DECIMAL(10,2) DEFAULT NULL COMMENT '净利润',
    net_margin          DECIMAL(5,4) DEFAULT NULL COMMENT '净利润率',
    roi                 DECIMAL(8,4) DEFAULT NULL COMMENT 'ROI',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='利润计算记录表';
