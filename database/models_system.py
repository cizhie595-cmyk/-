"""
系统运维与商业化模型层
包含: CrawlLogModel, ApiUsageLogModel, UsageRecordModel, SubscriptionLogModel,
      AffiliateClickModel, SystemConfigModel, AuditLogModel, NotificationModel,
      TeamModel, TeamMemberModel, TeamInvitationModel, MigrationModel
对应表: crawl_logs, api_usage_logs, usage_records, subscription_logs,
        affiliate_clicks, system_config, audit_logs, notifications,
        teams, team_members, team_invitations, _migrations
"""

import json
from datetime import datetime
from typing import Optional
from database.connection import db


class CrawlLogModel:
    """爬虫日志模型 - 对应 crawl_logs 表"""

    @staticmethod
    def create(task_type: str, target_id: int = None, message: str = None) -> int:
        sql = """INSERT INTO crawl_logs (task_type, target_id, status, message)
                 VALUES (%s, %s, 'running', %s)"""
        return db.insert_and_get_id(sql, (task_type, target_id, message))

    @staticmethod
    def update_status(log_id: int, status: str, message: str = None):
        sql = "UPDATE crawl_logs SET status = %s, message = %s, finished_at = NOW() WHERE id = %s"
        db.execute(sql, (status, message, log_id))

    @staticmethod
    def success(log_id: int, message: str = None):
        CrawlLogModel.update_status(log_id, "success", message)

    @staticmethod
    def fail(log_id: int, message: str = None):
        CrawlLogModel.update_status(log_id, "failed", message)

    @staticmethod
    def get_recent(task_type: str = None, limit: int = 50) -> list[dict]:
        sql = "SELECT * FROM crawl_logs"
        params = []
        if task_type:
            sql += " WHERE task_type = %s"
            params.append(task_type)
        sql += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_running() -> list[dict]:
        return db.fetch_all(
            "SELECT * FROM crawl_logs WHERE status = 'running' ORDER BY started_at DESC")

    @staticmethod
    def count_by_status(task_type: str = None) -> dict:
        """统计各状态的任务数量"""
        sql = "SELECT status, COUNT(*) AS cnt FROM crawl_logs"
        params = []
        if task_type:
            sql += " WHERE task_type = %s"
            params.append(task_type)
        sql += " GROUP BY status"
        rows = db.fetch_all(sql, tuple(params))
        return {r["status"]: r["cnt"] for r in rows}


class ApiUsageLogModel:
    """API 使用日志模型 - 对应 api_usage_logs 表"""

    @staticmethod
    def log(user_id: int, service_id: str, endpoint: str = None,
            tokens_used: int = 0, cost_usd: float = 0, status: str = "success",
            error_message: str = None) -> int:
        sql = """INSERT INTO api_usage_logs
                 (user_id, service_id, endpoint, tokens_used, cost_usd, status, error_message)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (
            user_id, service_id, endpoint, tokens_used, cost_usd, status, error_message))

    @staticmethod
    def get_by_user(user_id: int, service_id: str = None, days: int = 30) -> list[dict]:
        sql = """SELECT * FROM api_usage_logs WHERE user_id = %s
                 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"""
        params = [user_id, days]
        if service_id:
            sql += " AND service_id = %s"
            params.append(service_id)
        sql += " ORDER BY created_at DESC"
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_usage_summary(user_id: int, days: int = 30) -> list[dict]:
        """获取用户 API 使用汇总"""
        sql = """SELECT service_id, COUNT(*) AS call_count,
                 SUM(tokens_used) AS total_tokens, SUM(cost_usd) AS total_cost
                 FROM api_usage_logs WHERE user_id = %s
                 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                 GROUP BY service_id"""
        return db.fetch_all(sql, (user_id, days))

    @staticmethod
    def get_daily_stats(user_id: int, days: int = 30) -> list[dict]:
        """获取每日 API 调用统计"""
        sql = """SELECT DATE(created_at) AS log_date, service_id,
                 COUNT(*) AS call_count, SUM(tokens_used) AS tokens
                 FROM api_usage_logs WHERE user_id = %s
                 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                 GROUP BY log_date, service_id ORDER BY log_date DESC"""
        return db.fetch_all(sql, (user_id, days))


class UsageRecordModel:
    """配额使用记录模型 - 对应 usage_records 表"""

    @staticmethod
    def record(user_id: int, action_type: str, resource_id: str = None,
               credits_used: int = 1) -> int:
        sql = """INSERT INTO usage_records (user_id, action_type, resource_id, credits_used)
                 VALUES (%s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (user_id, action_type, resource_id, credits_used))

    @staticmethod
    def get_monthly_usage(user_id: int) -> dict:
        """获取当月各操作类型的使用量"""
        sql = """SELECT action_type, SUM(credits_used) AS total_credits, COUNT(*) AS count
                 FROM usage_records WHERE user_id = %s
                 AND created_at >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
                 GROUP BY action_type"""
        rows = db.fetch_all(sql, (user_id,))
        return {r["action_type"]: {"credits": r["total_credits"], "count": r["count"]}
                for r in rows}

    @staticmethod
    def get_total_credits(user_id: int, action_type: str = None) -> int:
        sql = """SELECT COALESCE(SUM(credits_used), 0) AS total FROM usage_records
                 WHERE user_id = %s AND created_at >= DATE_FORMAT(NOW(), '%%Y-%%m-01')"""
        params = [user_id]
        if action_type:
            sql += " AND action_type = %s"
            params.append(action_type)
        result = db.fetch_one(sql, tuple(params))
        return result["total"] if result else 0


class SubscriptionLogModel:
    """订阅日志模型 - 对应 subscription_logs 表"""

    @staticmethod
    def log(user_id: int, action: str, plan_from: str = None, plan_to: str = None,
            amount: float = None, currency: str = "USD", stripe_event_id: str = None) -> int:
        sql = """INSERT INTO subscription_logs
                 (user_id, action, plan_from, plan_to, amount, currency, stripe_event_id)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (
            user_id, action, plan_from, plan_to, amount, currency, stripe_event_id))

    @staticmethod
    def get_by_user(user_id: int) -> list[dict]:
        sql = "SELECT * FROM subscription_logs WHERE user_id = %s ORDER BY created_at DESC"
        return db.fetch_all(sql, (user_id,))

    @staticmethod
    def get_revenue_summary(days: int = 30) -> dict:
        """获取收入汇总"""
        sql = """SELECT currency, SUM(amount) AS total_amount, COUNT(*) AS tx_count
                 FROM subscription_logs WHERE action IN ('subscribe', 'upgrade', 'renew')
                 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                 GROUP BY currency"""
        return db.fetch_all(sql, (days,))


class AffiliateClickModel:
    """返佣点击模型 - 对应 affiliate_clicks 表"""

    @staticmethod
    def record(platform: str, product_id: str, affiliate_tag: str = None,
               click_url: str = None, user_id: int = None,
               ip_address: str = None, user_agent: str = None) -> int:
        sql = """INSERT INTO affiliate_clicks
                 (user_id, platform, product_id, affiliate_tag, click_url, ip_address, user_agent)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (
            user_id, platform, product_id, affiliate_tag, click_url, ip_address, user_agent))

    @staticmethod
    def get_stats(days: int = 30) -> list[dict]:
        """获取点击统计"""
        sql = """SELECT platform, COUNT(*) AS clicks, COUNT(DISTINCT product_id) AS products
                 FROM affiliate_clicks
                 WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                 GROUP BY platform"""
        return db.fetch_all(sql, (days,))

    @staticmethod
    def get_by_user(user_id: int, days: int = 30) -> list[dict]:
        sql = """SELECT * FROM affiliate_clicks WHERE user_id = %s
                 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                 ORDER BY created_at DESC"""
        return db.fetch_all(sql, (user_id, days))


class SystemConfigModel:
    """系统配置模型 - 对应 system_config 表"""

    @staticmethod
    def get(key: str) -> Optional[str]:
        result = db.fetch_one(
            "SELECT config_value FROM system_config WHERE config_key = %s", (key,))
        return result["config_value"] if result else None

    @staticmethod
    def set(key: str, value: str, description: str = None):
        sql = """INSERT INTO system_config (config_key, config_value, description)
                 VALUES (%s, %s, %s)
                 ON DUPLICATE KEY UPDATE config_value = VALUES(config_value),
                 description = COALESCE(VALUES(description), description)"""
        db.execute(sql, (key, value, description))

    @staticmethod
    def get_all() -> dict:
        rows = db.fetch_all("SELECT config_key, config_value FROM system_config")
        return {r["config_key"]: r["config_value"] for r in rows}

    @staticmethod
    def delete(key: str):
        db.execute("DELETE FROM system_config WHERE config_key = %s", (key,))


class AuditLogModel:
    """审计日志模型 - 对应 audit_logs 表"""

    @staticmethod
    def log(action: str, user_id: int = None, resource_type: str = None,
            resource_id: str = None, details: dict = None,
            ip_address: str = None, user_agent: str = None) -> int:
        sql = """INSERT INTO audit_logs
                 (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (
            user_id, action, resource_type, resource_id,
            json.dumps(details) if details else None, ip_address, user_agent))

    @staticmethod
    def get_by_user(user_id: int, page: int = 1, per_page: int = 50) -> list[dict]:
        offset = (page - 1) * per_page
        sql = """SELECT * FROM audit_logs WHERE user_id = %s
                 ORDER BY created_at DESC LIMIT %s OFFSET %s"""
        return db.fetch_all(sql, (user_id, per_page, offset))

    @staticmethod
    def get_by_resource(resource_type: str, resource_id: str) -> list[dict]:
        sql = """SELECT * FROM audit_logs WHERE resource_type = %s AND resource_id = %s
                 ORDER BY created_at DESC"""
        return db.fetch_all(sql, (resource_type, resource_id))

    @staticmethod
    def get_recent(limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT %s"
        return db.fetch_all(sql, (limit,))


class NotificationModel:
    """通知模型 - 对应 notifications 表"""

    @staticmethod
    def create(user_id: int, type_: str, title: str, message: str = None,
               link: str = None) -> int:
        sql = """INSERT INTO notifications (user_id, type, title, message, link)
                 VALUES (%s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (user_id, type_, title, message, link))

    @staticmethod
    def get_by_user(user_id: int, unread_only: bool = False,
                    page: int = 1, per_page: int = 20) -> list[dict]:
        offset = (page - 1) * per_page
        sql = "SELECT * FROM notifications WHERE user_id = %s"
        params = [user_id]
        if unread_only:
            sql += " AND is_read = 0"
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def mark_read(notification_id: int):
        db.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notification_id,))

    @staticmethod
    def mark_all_read(user_id: int):
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
                   (user_id,))

    @staticmethod
    def unread_count(user_id: int) -> int:
        result = db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0",
            (user_id,))
        return result["cnt"] if result else 0

    @staticmethod
    def delete(notification_id: int):
        db.execute("DELETE FROM notifications WHERE id = %s", (notification_id,))

    @staticmethod
    def delete_old(user_id: int, days: int = 90):
        """删除指定天数前的已读通知"""
        sql = """DELETE FROM notifications WHERE user_id = %s AND is_read = 1
                 AND created_at < DATE_SUB(NOW(), INTERVAL %s DAY)"""
        db.execute(sql, (user_id, days))


class TeamModel:
    """团队模型 - 对应 teams 表"""

    @staticmethod
    def create(name: str, owner_id: int, description: str = None,
               max_members: int = 5) -> int:
        sql = """INSERT INTO teams (name, owner_id, description, max_members)
                 VALUES (%s, %s, %s, %s)"""
        team_id = db.insert_and_get_id(sql, (name, owner_id, description, max_members))
        # 自动将创建者添加为 owner 成员
        TeamMemberModel.add(team_id, owner_id, role="owner")
        return team_id

    @staticmethod
    def get_by_id(team_id: int) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM teams WHERE id = %s", (team_id,))

    @staticmethod
    def get_by_owner(owner_id: int) -> list[dict]:
        return db.fetch_all(
            "SELECT * FROM teams WHERE owner_id = %s ORDER BY created_at DESC", (owner_id,))

    @staticmethod
    def get_user_teams(user_id: int) -> list[dict]:
        """获取用户所属的所有团队"""
        sql = """SELECT t.* FROM teams t
                 JOIN team_members tm ON t.id = tm.team_id
                 WHERE tm.user_id = %s ORDER BY t.created_at DESC"""
        return db.fetch_all(sql, (user_id,))

    @staticmethod
    def update(team_id: int, data: dict):
        if not data:
            return
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE teams SET {set_clause} WHERE id = %s"
        db.execute(sql, (*data.values(), team_id))

    @staticmethod
    def delete(team_id: int):
        db.execute("DELETE FROM team_invitations WHERE team_id = %s", (team_id,))
        db.execute("DELETE FROM team_members WHERE team_id = %s", (team_id,))
        db.execute("DELETE FROM teams WHERE id = %s", (team_id,))


class TeamMemberModel:
    """团队成员模型 - 对应 team_members 表"""

    @staticmethod
    def add(team_id: int, user_id: int, role: str = "member") -> int:
        sql = "INSERT INTO team_members (team_id, user_id, role) VALUES (%s, %s, %s)"
        return db.insert_and_get_id(sql, (team_id, user_id, role))

    @staticmethod
    def get_members(team_id: int) -> list[dict]:
        sql = """SELECT tm.*, u.username, u.email, u.avatar_url
                 FROM team_members tm JOIN users u ON tm.user_id = u.id
                 WHERE tm.team_id = %s ORDER BY tm.joined_at ASC"""
        return db.fetch_all(sql, (team_id,))

    @staticmethod
    def get_member(team_id: int, user_id: int) -> Optional[dict]:
        sql = "SELECT * FROM team_members WHERE team_id = %s AND user_id = %s"
        return db.fetch_one(sql, (team_id, user_id))

    @staticmethod
    def update_role(team_id: int, user_id: int, role: str):
        sql = "UPDATE team_members SET role = %s WHERE team_id = %s AND user_id = %s"
        db.execute(sql, (role, team_id, user_id))

    @staticmethod
    def remove(team_id: int, user_id: int):
        db.execute(
            "DELETE FROM team_members WHERE team_id = %s AND user_id = %s", (team_id, user_id))

    @staticmethod
    def count(team_id: int) -> int:
        result = db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM team_members WHERE team_id = %s", (team_id,))
        return result["cnt"] if result else 0


class TeamInvitationModel:
    """团队邀请模型 - 对应 team_invitations 表"""

    @staticmethod
    def create(team_id: int, email: str, invited_by: int, role: str = "member",
               token: str = None, expires_hours: int = 72) -> int:
        import secrets
        if not token:
            token = secrets.token_urlsafe(32)
        sql = """INSERT INTO team_invitations
                 (team_id, email, role, token, invited_by, expires_at)
                 VALUES (%s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL %s HOUR))"""
        return db.insert_and_get_id(sql, (team_id, email, role, token, invited_by, expires_hours))

    @staticmethod
    def get_by_token(token: str) -> Optional[dict]:
        return db.fetch_one(
            "SELECT * FROM team_invitations WHERE token = %s AND status = 'pending'", (token,))

    @staticmethod
    def get_by_team(team_id: int) -> list[dict]:
        sql = "SELECT * FROM team_invitations WHERE team_id = %s ORDER BY created_at DESC"
        return db.fetch_all(sql, (team_id,))

    @staticmethod
    def accept(invitation_id: int):
        db.execute(
            "UPDATE team_invitations SET status = 'accepted' WHERE id = %s", (invitation_id,))

    @staticmethod
    def expire_old():
        """将过期的邀请标记为 expired"""
        db.execute(
            "UPDATE team_invitations SET status = 'expired' WHERE status = 'pending' AND expires_at < NOW()")

    @staticmethod
    def get_pending_by_email(email: str) -> list[dict]:
        sql = """SELECT ti.*, t.name AS team_name FROM team_invitations ti
                 JOIN teams t ON ti.team_id = t.id
                 WHERE ti.email = %s AND ti.status = 'pending' AND ti.expires_at > NOW()"""
        return db.fetch_all(sql, (email,))


class MigrationModel:
    """数据库迁移记录模型 - 对应 _migrations 表"""

    @staticmethod
    def get_executed() -> list[str]:
        """获取已执行的迁移文件名列表"""
        rows = db.fetch_all("SELECT filename FROM _migrations ORDER BY executed_at ASC")
        return [r["filename"] for r in rows]

    @staticmethod
    def record(filename: str):
        """记录已执行的迁移"""
        db.execute("INSERT INTO _migrations (filename) VALUES (%s)", (filename,))

    @staticmethod
    def is_executed(filename: str) -> bool:
        result = db.fetch_one(
            "SELECT id FROM _migrations WHERE filename = %s", (filename,))
        return result is not None
