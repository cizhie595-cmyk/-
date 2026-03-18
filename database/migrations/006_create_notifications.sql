-- ============================================================
-- Migration 006: 创建通知表
-- Coupang 选品系统 - 站内通知
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL COMMENT '目标用户ID',
    type            VARCHAR(50) NOT NULL COMMENT '通知类型',
    title           VARCHAR(200) NOT NULL COMMENT '通知标题',
    message         TEXT NULL COMMENT '通知内容',
    data            JSON NULL COMMENT '附加数据',
    is_read         TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已读',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_read (user_id, is_read),
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_type (type),
    CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='站内通知表';
