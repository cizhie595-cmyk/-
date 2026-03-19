-- Migration 009: 新增分析模块数据表
-- 竞品监控追踪、关键词研究、供应商评分、定价策略优化

-- ============================================================
-- 竞品监控表 (Step 2: competitor_tracker)
-- ============================================================
CREATE TABLE IF NOT EXISTS competitor_monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    asin VARCHAR(20) NOT NULL,
    marketplace VARCHAR(10) DEFAULT 'US',
    label VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, asin, marketplace)
);

CREATE INDEX IF NOT EXISTS idx_competitor_monitors_user
    ON competitor_monitors(user_id, is_active);

-- 竞品快照表 (每次监控抓取的数据)
CREATE TABLE IF NOT EXISTS competitor_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL,
    asin VARCHAR(20) NOT NULL,
    price REAL,
    bsr_rank INTEGER,
    bsr_category VARCHAR(200),
    rating REAL,
    review_count INTEGER,
    seller_count INTEGER,
    fulfillment VARCHAR(20),
    stock_status VARCHAR(50),
    buy_box_seller VARCHAR(200),
    title VARCHAR(500),
    main_image_url TEXT,
    snapshot_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (monitor_id) REFERENCES competitor_monitors(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_monitor
    ON competitor_snapshots(monitor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_asin
    ON competitor_snapshots(asin, created_at DESC);

-- 竞品变动告警表
CREATE TABLE IF NOT EXISTS competitor_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    old_value REAL,
    new_value REAL,
    change_pct REAL,
    message TEXT,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (monitor_id) REFERENCES competitor_monitors(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_competitor_alerts_monitor
    ON competitor_alerts(monitor_id, is_read, created_at DESC);

-- ============================================================
-- 关键词研究表 (Step 3: keyword_researcher)
-- ============================================================
CREATE TABLE IF NOT EXISTS keyword_research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    seed_keyword VARCHAR(200) NOT NULL,
    marketplace VARCHAR(10) DEFAULT 'US',
    difficulty_score REAL,
    difficulty_level VARCHAR(20),
    estimated_monthly_searches INTEGER,
    search_volume_tier VARCHAR(20),
    competition_summary TEXT,
    recommendations JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_keyword_research_user
    ON keyword_research(user_id, created_at DESC);

-- 关键词建议表 (长尾词/自动补全)
CREATE TABLE IF NOT EXISTS keyword_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_id INTEGER NOT NULL,
    keyword VARCHAR(300) NOT NULL,
    source VARCHAR(50),
    category VARCHAR(50),
    estimated_volume INTEGER,
    difficulty_score REAL,
    priority_score REAL,
    priority_tier VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (research_id) REFERENCES keyword_research(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_keyword_suggestions_research
    ON keyword_suggestions(research_id, priority_score DESC);

-- ============================================================
-- 供应商评分表 (Step 8: supplier_scorer)
-- ============================================================
CREATE TABLE IF NOT EXISTS supplier_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    supplier_name VARCHAR(200),
    supplier_url TEXT,
    total_score REAL,
    grade VARCHAR(5),
    credibility_score REAL,
    product_capability_score REAL,
    service_quality_score REAL,
    price_competitiveness_score REAL,
    logistics_score REAL,
    strengths JSON,
    weaknesses JSON,
    recommendation TEXT,
    raw_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_supplier_scores_user
    ON supplier_scores(user_id, project_id, total_score DESC);

-- ============================================================
-- 定价策略分析表 (Step 9: pricing_optimizer)
-- ============================================================
CREATE TABLE IF NOT EXISTS pricing_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    asin VARCHAR(20),
    marketplace VARCHAR(10) DEFAULT 'US',
    strategy_name VARCHAR(50),
    optimal_price REAL,
    price_floor REAL,
    price_ceiling REAL,
    breakeven_price REAL,
    target_margin_pct REAL,
    expected_profit_per_unit REAL,
    expected_margin_pct REAL,
    market_avg_price REAL,
    market_median_price REAL,
    cost_breakdown JSON,
    elasticity_data JSON,
    strategy_comparison JSON,
    distribution_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pricing_analyses_user
    ON pricing_analyses(user_id, project_id, created_at DESC);
