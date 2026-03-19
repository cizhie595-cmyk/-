-- Migration 010: 新增产品洞察模块数据表
-- BSR 历史追踪、竞品关系、情感分析、AI 决策结果
-- Created: 2026-03-19

-- ============================================================
-- BSR 历史快照表
-- ============================================================
CREATE TABLE IF NOT EXISTS bsr_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    marketplace VARCHAR(10) NOT NULL DEFAULT 'US',
    bsr_rank INT,
    price DECIMAL(10, 2),
    rating DECIMAL(3, 2),
    review_count INT,
    est_sales INT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bsr_asin (asin),
    INDEX idx_bsr_marketplace (marketplace),
    INDEX idx_bsr_recorded (recorded_at),
    INDEX idx_bsr_asin_time (asin, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 竞品关系表
-- ============================================================
CREATE TABLE IF NOT EXISTS competitor_relations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_asin VARCHAR(20) NOT NULL COMMENT '源产品 ASIN',
    target_asin VARCHAR(20) NOT NULL COMMENT '竞品 ASIN',
    marketplace VARCHAR(10) NOT NULL DEFAULT 'US',
    relation_type ENUM('direct', 'indirect', 'substitute', 'complementary') DEFAULT 'direct',
    similarity_score DECIMAL(5, 4) COMMENT '相似度评分 0-1',
    price_diff_pct DECIMAL(8, 2) COMMENT '价格差异百分比',
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_comp_source (source_asin),
    INDEX idx_comp_target (target_asin),
    UNIQUE KEY uk_competitor_pair (source_asin, target_asin, marketplace)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 竞争格局分析快照表
-- ============================================================
CREATE TABLE IF NOT EXISTS landscape_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(200) NOT NULL,
    marketplace VARCHAR(10) NOT NULL DEFAULT 'US',
    total_products INT,
    avg_price DECIMAL(10, 2),
    avg_rating DECIMAL(3, 2),
    avg_reviews INT,
    fba_ratio DECIMAL(5, 4),
    brand_concentration DECIMAL(5, 4),
    price_tiers JSON COMMENT '价格区间分布',
    market_gaps JSON COMMENT '市场空白分析',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_landscape_keyword (keyword),
    INDEX idx_landscape_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 评论情感分析结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS sentiment_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    marketplace VARCHAR(10) NOT NULL DEFAULT 'US',
    total_reviews INT,
    positive_count INT,
    neutral_count INT,
    negative_count INT,
    positive_pct DECIMAL(5, 2),
    neutral_pct DECIMAL(5, 2),
    negative_pct DECIMAL(5, 2),
    avg_sentiment DECIMAL(5, 4) COMMENT '平均情感分 -1 到 1',
    top_tags JSON COMMENT '高频标签',
    wordcloud_data JSON COMMENT '词云数据',
    trend_data JSON COMMENT '情感趋势数据',
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sentiment_asin (asin),
    INDEX idx_sentiment_time (analyzed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- AI 选品决策结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS decision_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    marketplace VARCHAR(10) NOT NULL DEFAULT 'US',
    overall_score INT COMMENT '综合评分 0-100',
    decision ENUM('GO', 'CONSIDER', 'CAUTION', 'NO_GO') NOT NULL,
    market_score INT,
    competition_score INT,
    profit_score INT,
    risk_score INT,
    demand_score INT,
    risk_scores JSON COMMENT '五维风险评分',
    strengths JSON COMMENT '优势列表',
    weaknesses JSON COMMENT '劣势列表',
    recommendation TEXT COMMENT 'AI 推荐建议',
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_decision_asin (asin),
    INDEX idx_decision_score (overall_score),
    INDEX idx_decision_time (evaluated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 看板统计缓存表
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboard_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    cache_key VARCHAR(100) NOT NULL,
    cache_data JSON NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cache_user (user_id),
    UNIQUE KEY uk_cache_key (user_id, cache_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
