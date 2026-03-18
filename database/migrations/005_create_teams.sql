-- ============================================================
-- Migration 005: 创建团队协作相关表
-- Coupang 选品系统 - 团队/成员/邀请
-- ============================================================

-- 团队表
CREATE TABLE IF NOT EXISTS teams (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL COMMENT '团队名称',
    description     VARCHAR(500) NULL COMMENT '团队描述',
    owner_id        INT NOT NULL COMMENT '创建者/拥有者ID',
    invite_code     VARCHAR(50) NOT NULL COMMENT '邀请码',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_invite_code (invite_code),
    INDEX idx_owner_id (owner_id),
    CONSTRAINT fk_team_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='团队表';

-- 团队成员表
CREATE TABLE IF NOT EXISTS team_members (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    team_id         INT NOT NULL COMMENT '团队ID',
    user_id         INT NOT NULL COMMENT '用户ID',
    role            VARCHAR(20) NOT NULL DEFAULT 'viewer' COMMENT '角色: owner/admin/analyst/viewer',
    joined_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_team_user (team_id, user_id),
    INDEX idx_user_id (user_id),
    CONSTRAINT fk_member_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT fk_member_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='团队成员表';

-- 团队邀请表
CREATE TABLE IF NOT EXISTS team_invitations (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    team_id         INT NOT NULL COMMENT '团队ID',
    email           VARCHAR(255) NOT NULL COMMENT '被邀请人邮箱',
    role            VARCHAR(20) NOT NULL DEFAULT 'analyst' COMMENT '分配角色',
    token           VARCHAR(100) NOT NULL COMMENT '邀请 Token',
    inviter_id      INT NOT NULL COMMENT '邀请人ID',
    accepted        TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已接受',
    expires_at      DATETIME NOT NULL COMMENT '过期时间',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_token (token),
    INDEX idx_team_email (team_id, email),
    CONSTRAINT fk_invite_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='团队邀请表';
