-- ============================================================
-- 迁移脚本 003: 商业化模块（订阅系统 + Affiliate 返佣）
-- 执行方式: mysql -u root -p coupang_selection < database/migrations/003_add_monetization.sql
-- ============================================================

-- 1. 在 users 表中增加订阅相关字段
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(20) DEFAULT 'free'
        COMMENT '订阅计划(free/orbit/moonshot)' AFTER api_keys_settings,
    ADD COLUMN IF NOT EXISTS subscription_started_at DATETIME DEFAULT NULL
        COMMENT '订阅开始时间' AFTER subscription_plan,
    ADD COLUMN IF NOT EXISTS subscription_expires_at DATETIME DEFAULT NULL
        COMMENT '订阅到期时间' AFTER subscription_started_at,
    ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20) DEFAULT 'monthly'
        COMMENT '计费周期(monthly/yearly/cancelled)' AFTER subscription_expires_at;

-- 2. 使用量记录表
CREATE TABLE IF NOT EXISTS usage_records (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    quota_type      VARCHAR(50) NOT NULL COMMENT '配额类型',
    count           INT DEFAULT 1 COMMENT '使用次数',
    recorded_date   DATE NOT NULL COMMENT '记录日期',

    UNIQUE KEY uk_user_quota_date (user_id, quota_type, recorded_date),
    INDEX idx_user_date (user_id, recorded_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='功能使用量记录';

-- 3. 订阅变更日志表
CREATE TABLE IF NOT EXISTS subscription_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    plan_id         VARCHAR(20) NOT NULL,
    billing_cycle   VARCHAR(20) DEFAULT 'monthly',
    started_at      DATETIME NOT NULL,
    expires_at      DATETIME NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订阅变更日志';

-- 4. Affiliate 点击追踪表
CREATE TABLE IF NOT EXISTS affiliate_clicks (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    asin            VARCHAR(20) NOT NULL,
    marketplace     VARCHAR(10) DEFAULT 'US',
    tag_used        VARCHAR(100) DEFAULT NULL,
    clicked_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_id (user_id),
    INDEX idx_asin (asin),
    INDEX idx_clicked_at (clicked_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Affiliate点击追踪';

-- 5. 系统配置表（存储 Affiliate Tag 等全局配置）
CREATE TABLE IF NOT EXISTS system_config (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    config_key      VARCHAR(100) NOT NULL UNIQUE,
    config_value    TEXT DEFAULT NULL,
    description     VARCHAR(255) DEFAULT NULL,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统全局配置';

-- 插入默认的 Affiliate Tag 配置（管理员后续修改）
INSERT IGNORE INTO system_config (config_key, config_value, description) VALUES
    ('affiliate_tag_amazon_us', '', 'Amazon US Associates Tag'),
    ('affiliate_tag_amazon_uk', '', 'Amazon UK Associates Tag'),
    ('affiliate_tag_amazon_de', '', 'Amazon DE Associates Tag'),
    ('affiliate_tag_amazon_jp', '', 'Amazon JP Associates Tag'),
    ('affiliate_tag_amazon_ca', '', 'Amazon CA Associates Tag'),
    ('affiliate_tag_coupang', '', 'Coupang Partners Tag');
