-- ============================================================
-- Migration 003: 创建审计日志表
-- Coupang 选品系统 - 操作日志/审计日志
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NULL COMMENT '操作用户ID (NULL 表示系统操作)',
    action          VARCHAR(50) NOT NULL COMMENT '操作类型',
    target_type     VARCHAR(50) NULL COMMENT '操作目标类型 (user/project/subscription)',
    target_id       VARCHAR(100) NULL COMMENT '操作目标ID',
    details         JSON NULL COMMENT '操作详情 (JSON)',
    status          VARCHAR(20) NOT NULL DEFAULT 'success' COMMENT '操作状态 (success/failed/error)',
    ip_address      VARCHAR(45) NULL COMMENT '操作者IP地址',
    user_agent      VARCHAR(500) NULL COMMENT '浏览器 User-Agent',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_target (target_type, target_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_user_action_time (user_id, action, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='审计日志表';
