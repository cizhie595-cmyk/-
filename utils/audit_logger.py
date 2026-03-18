"""
Coupang 选品系统 - 操作日志/审计日志系统
记录用户关键操作，支持查询和导出
"""

import json
from datetime import datetime
from typing import Optional
from flask import request, g
from utils.logger import get_logger

logger = get_logger()


class AuditLogger:
    """审计日志记录器"""

    # 操作类型常量
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_REGISTER = "register"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_PASSWORD_RESET = "password_reset"
    ACTION_PROFILE_UPDATE = "profile_update"
    ACTION_EMAIL_VERIFY = "email_verify"
    ACTION_SUBSCRIPTION_UPGRADE = "subscription_upgrade"
    ACTION_SUBSCRIPTION_CANCEL = "subscription_cancel"
    ACTION_PROJECT_CREATE = "project_create"
    ACTION_PROJECT_UPDATE = "project_update"
    ACTION_PROJECT_DELETE = "project_delete"
    ACTION_PROJECT_RUN = "project_run"
    ACTION_ANALYSIS_START = "analysis_start"
    ACTION_3D_GENERATE = "3d_generate"
    ACTION_REPORT_GENERATE = "report_generate"
    ACTION_DATA_EXPORT = "data_export"
    ACTION_API_KEY_UPDATE = "api_key_update"
    ACTION_ADMIN_USER_UPDATE = "admin_user_update"
    ACTION_ADMIN_USER_DISABLE = "admin_user_disable"

    @staticmethod
    def log(action: str, user_id: int = None, target_type: str = None,
            target_id: str = None, details: dict = None,
            status: str = "success", ip: str = None):
        """
        记录审计日志

        :param action: 操作类型 (参见 ACTION_* 常量)
        :param user_id: 操作用户ID
        :param target_type: 操作目标类型 (user/project/subscription 等)
        :param target_id: 操作目标ID
        :param details: 操作详情 (JSON 序列化)
        :param status: 操作状态 (success/failed/error)
        :param ip: 操作者IP
        """
        # 自动获取用户信息
        if user_id is None:
            current_user = getattr(g, "current_user", None) if g else None
            if current_user:
                user_id = current_user.get("user_id") or current_user.get("sub")

        # 自动获取 IP
        if ip is None:
            try:
                ip = request.remote_addr if request else None
            except RuntimeError:
                ip = None

        # 获取 User-Agent
        user_agent = None
        try:
            user_agent = request.headers.get("User-Agent", "")[:500] if request else None
        except RuntimeError:
            pass

        try:
            from database.connection import db
            db.execute(
                """INSERT INTO audit_logs
                   (user_id, action, target_type, target_id,
                    details, status, ip_address, user_agent, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                (
                    user_id,
                    action,
                    target_type,
                    str(target_id) if target_id else None,
                    json.dumps(details, ensure_ascii=False) if details else None,
                    status,
                    ip,
                    user_agent,
                ),
            )
        except Exception as e:
            # 审计日志写入失败不应影响主流程
            logger.error(f"[AuditLog] 写入失败: action={action}, user_id={user_id}, error={e}")

    @staticmethod
    def query(user_id: int = None, action: str = None,
              target_type: str = None, status: str = None,
              start_date: str = None, end_date: str = None,
              page: int = 1, page_size: int = 50) -> dict:
        """
        查询审计日志

        :return: {"logs": [...], "total": int, "page": int, "page_size": int}
        """
        try:
            from database.connection import db

            conditions = []
            params = []

            if user_id:
                conditions.append("user_id = %s")
                params.append(user_id)
            if action:
                conditions.append("action = %s")
                params.append(action)
            if target_type:
                conditions.append("target_type = %s")
                params.append(target_type)
            if status:
                conditions.append("status = %s")
                params.append(status)
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            offset = (page - 1) * page_size

            # 查询总数
            total_row = db.fetch_one(
                f"SELECT COUNT(*) AS total FROM audit_logs WHERE {where_clause}",
                tuple(params),
            )
            total = total_row["total"] if total_row else 0

            # 查询日志
            logs = db.fetch_all(
                f"""SELECT id, user_id, action, target_type, target_id,
                           details, status, ip_address, created_at
                    FROM audit_logs
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s""",
                (*params, page_size, offset),
            )

            # 解析 details JSON
            for log_entry in logs:
                if log_entry.get("details"):
                    try:
                        log_entry["details"] = json.loads(log_entry["details"])
                    except (json.JSONDecodeError, TypeError):
                        pass

            return {
                "logs": logs,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except Exception as e:
            logger.error(f"[AuditLog] 查询失败: {e}")
            return {"logs": [], "total": 0, "page": page, "page_size": page_size}


# 全局审计日志实例
audit = AuditLogger()
