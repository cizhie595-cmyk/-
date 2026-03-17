-- ============================================================
-- Coupang 跨境电商智能选品系统 - 用户模块建表脚本
-- 数据库引擎: MySQL 8.0+
-- 字符集: utf8mb4
-- 创建时间: 2026-03-18
-- ============================================================

USE coupang_selection;

-- ============================================================
-- 14. 用户表 (users)
-- 存储系统用户的账号信息
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    username            VARCHAR(50) NOT NULL COMMENT '用户名(唯一)',
    email               VARCHAR(200) NOT NULL COMMENT '邮箱(唯一)',
    password_hash       VARCHAR(255) NOT NULL COMMENT '密码哈希(bcrypt)',
    nickname            VARCHAR(100) DEFAULT NULL COMMENT '昵称/显示名',
    avatar_url          VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    phone               VARCHAR(30) DEFAULT NULL COMMENT '手机号',

    -- 角色与权限
    role                ENUM('admin', 'user', 'viewer') DEFAULT 'user' COMMENT '角色: 管理员/普通用户/只读用户',
    is_active           TINYINT(1) DEFAULT 1 COMMENT '是否激活(0=禁用, 1=激活)',
    is_verified         TINYINT(1) DEFAULT 0 COMMENT '邮箱是否已验证(0=未验证, 1=已验证)',

    -- OpenAI API 配置（每个用户可配置自己的Key）
    openai_api_key      VARCHAR(255) DEFAULT NULL COMMENT '用户自己的OpenAI API Key(加密存储)',
    openai_model        VARCHAR(100) DEFAULT 'gpt-4' COMMENT '用户选择的AI模型',

    -- Coupang 卖家账号（每个用户可绑定自己的账号）
    coupang_seller_email    VARCHAR(200) DEFAULT NULL COMMENT 'Coupang卖家邮箱',
    coupang_seller_password VARCHAR(255) DEFAULT NULL COMMENT 'Coupang卖家密码(加密存储)',

    -- Naver API 配置
    naver_client_id     VARCHAR(200) DEFAULT NULL COMMENT 'Naver API Client ID',
    naver_client_secret VARCHAR(200) DEFAULT NULL COMMENT 'Naver API Client Secret',

    -- 语言偏好
    language            ENUM('zh_CN', 'en_US', 'ko_KR') DEFAULT 'zh_CN' COMMENT '界面语言偏好',

    -- 使用统计
    last_login_at       DATETIME DEFAULT NULL COMMENT '最后登录时间',
    last_login_ip       VARCHAR(50) DEFAULT NULL COMMENT '最后登录IP',
    login_count         INT UNSIGNED DEFAULT 0 COMMENT '累计登录次数',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    INDEX idx_role (role),
    INDEX idx_active (is_active)
) ENGINE=InnoDB COMMENT='用户表';

-- ============================================================
-- 15. 用户登录日志表 (user_login_logs)
-- 记录用户的登录历史，用于安全审计
-- ============================================================
CREATE TABLE IF NOT EXISTS user_login_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    user_id         INT UNSIGNED NOT NULL COMMENT '用户ID',
    login_ip        VARCHAR(50) DEFAULT NULL COMMENT '登录IP',
    user_agent      VARCHAR(500) DEFAULT NULL COMMENT '浏览器UA',
    login_status    ENUM('success', 'failed', 'locked') NOT NULL COMMENT '登录状态',
    fail_reason     VARCHAR(200) DEFAULT NULL COMMENT '失败原因',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',

    INDEX idx_user (user_id),
    INDEX idx_status (login_status),
    INDEX idx_time (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='用户登录日志表';

-- ============================================================
-- 16. 用户选品任务表 (user_tasks)
-- 将选品任务与用户关联，支持多用户并行使用
-- ============================================================
CREATE TABLE IF NOT EXISTS user_tasks (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
    user_id         INT UNSIGNED NOT NULL COMMENT '用户ID',
    keyword_id      INT UNSIGNED DEFAULT NULL COMMENT '关联关键词ID',
    task_name       VARCHAR(200) DEFAULT NULL COMMENT '任务名称',
    task_status     ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    task_config     JSON DEFAULT NULL COMMENT '任务配置参数(JSON)',
    result_summary  JSON DEFAULT NULL COMMENT '任务结果摘要(JSON)',
    started_at      DATETIME DEFAULT NULL COMMENT '开始时间',
    finished_at     DATETIME DEFAULT NULL COMMENT '完成时间',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_user (user_id),
    INDEX idx_status (task_status),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='用户选品任务表';
