-- ============================================================
-- Migration 004: 创建 OAuth 第三方登录绑定表
-- Coupang 选品系统 - 支持 Google/GitHub OAuth 登录
-- ============================================================

CREATE TABLE IF NOT EXISTS user_oauth (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL COMMENT '关联用户ID',
    provider        VARCHAR(20) NOT NULL COMMENT 'OAuth 提供商 (google/github)',
    provider_id     VARCHAR(100) NOT NULL COMMENT '提供商用户ID',
    provider_name   VARCHAR(100) NULL COMMENT '提供商用户名',
    provider_avatar VARCHAR(500) NULL COMMENT '提供商头像 URL',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_provider_id (provider, provider_id),
    INDEX idx_user_id (user_id),

    CONSTRAINT fk_oauth_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='OAuth 第三方登录绑定表';

-- 为 users 表添加 email_verified 字段（如果不存在）
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified TINYINT(1) NOT NULL DEFAULT 0 AFTER email;
