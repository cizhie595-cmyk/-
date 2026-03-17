-- ============================================================
-- 迁移脚本 002: 增加第三方 API 密钥配置字段
-- 执行方式: mysql -u root -p coupang_selection < database/migrations/002_add_api_keys_settings.sql
-- ============================================================

-- 在 users 表中增加 api_keys_settings JSON 字段
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS api_keys_settings JSON DEFAULT NULL
    COMMENT '第三方API密钥配置(Amazon SP-API, Keepa, Meshy等)'
    AFTER ai_settings;

-- 创建 API 密钥使用日志表（用于追踪 API 调用量和费用）
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    service_id      VARCHAR(50) NOT NULL COMMENT '服务ID(keepa/meshy/rainforest等)',
    endpoint        VARCHAR(255) DEFAULT NULL COMMENT '调用的具体接口',
    tokens_used     INT DEFAULT 0 COMMENT '消耗的Token/积分数',
    cost_usd        DECIMAL(10, 4) DEFAULT 0 COMMENT '预估费用(美元)',
    status          VARCHAR(20) DEFAULT 'success' COMMENT 'success/failed',
    error_message   TEXT DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_service (user_id, service_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='第三方API调用日志';
