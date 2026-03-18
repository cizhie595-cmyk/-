"""
Coupang 选品系统 - 通知系统
支持: 站内通知 + 邮件通知
"""

import json
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 通知类型
# ============================================================

class NotificationType:
    """通知类型常量"""
    # 任务通知
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # 团队通知
    TEAM_INVITED = "team_invited"
    TEAM_JOINED = "team_joined"
    TEAM_ROLE_CHANGED = "team_role_changed"
    TEAM_REMOVED = "team_removed"

    # 订阅通知
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    QUOTA_LOW = "quota_low"
    QUOTA_EXHAUSTED = "quota_exhausted"

    # 系统通知
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    SYSTEM_MAINTENANCE = "system_maintenance"

    # 通知类型元数据
    METADATA = {
        "task_completed": {"label": "任务完成", "icon": "check-circle", "color": "success", "email": True},
        "task_failed": {"label": "任务失败", "icon": "x-circle", "color": "danger", "email": True},
        "team_invited": {"label": "团队邀请", "icon": "user-plus", "color": "info", "email": True},
        "team_joined": {"label": "成员加入", "icon": "users", "color": "info", "email": False},
        "team_role_changed": {"label": "角色变更", "icon": "shield", "color": "warning", "email": True},
        "team_removed": {"label": "被移出团队", "icon": "user-minus", "color": "danger", "email": True},
        "subscription_expiring": {"label": "订阅即将到期", "icon": "clock", "color": "warning", "email": True},
        "subscription_renewed": {"label": "订阅已续费", "icon": "credit-card", "color": "success", "email": True},
        "quota_low": {"label": "配额不足", "icon": "alert-triangle", "color": "warning", "email": True},
        "quota_exhausted": {"label": "配额已用完", "icon": "alert-circle", "color": "danger", "email": True},
        "system_announcement": {"label": "系统公告", "icon": "megaphone", "color": "info", "email": False},
        "system_maintenance": {"label": "维护通知", "icon": "tool", "color": "warning", "email": True},
    }


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            try:
                from database.connection import db
                self._db = db
            except Exception:
                pass
        return self._db

    def send(self, user_id: int, ntype: str, title: str, message: str,
             data: dict = None, send_email: bool = None) -> dict:
        """
        发送通知

        :param user_id: 目标用户ID
        :param ntype: 通知类型
        :param title: 通知标题
        :param message: 通知内容
        :param data: 附加数据 (JSON)
        :param send_email: 是否同时发邮件 (None=自动判断)
        :return: 结果 dict
        """
        db = self._get_db()

        # 1. 存储站内通知
        notification_id = None
        if db:
            try:
                notification_id = db.insert_and_get_id(
                    """INSERT INTO notifications
                       (user_id, type, title, message, data, is_read, created_at)
                       VALUES (%s, %s, %s, %s, %s, 0, NOW())""",
                    (user_id, ntype, title, message,
                     json.dumps(data, ensure_ascii=False) if data else None),
                )
            except Exception as e:
                logger.error(f"[Notification] 存储通知失败: {e}")

        # 2. 通过 SSE 实时推送
        try:
            from utils.task_notifier import sse_manager
            sse_manager.publish(user_id, {
                "type": "NOTIFICATION",
                "notification_id": notification_id,
                "ntype": ntype,
                "title": title,
                "message": message,
                "data": data,
                "timestamp": int(datetime.now().timestamp()),
            })
        except Exception:
            pass

        # 3. 发送邮件通知
        meta = NotificationType.METADATA.get(ntype, {})
        should_email = send_email if send_email is not None else meta.get("email", False)

        if should_email:
            self._send_email_notification(user_id, ntype, title, message, data)

        logger.info(f"[Notification] user={user_id} type={ntype} title={title}")
        return {"success": True, "notification_id": notification_id}

    def send_bulk(self, user_ids: list[int], ntype: str, title: str,
                  message: str, data: dict = None):
        """批量发送通知"""
        for uid in user_ids:
            self.send(uid, ntype, title, message, data)

    def get_notifications(self, user_id: int, page: int = 1, per_page: int = 20,
                          unread_only: bool = False) -> dict:
        """获取用户通知列表"""
        db = self._get_db()
        if not db:
            return {"success": True, "notifications": [], "total": 0, "unread_count": 0}

        try:
            offset = (page - 1) * per_page
            where = "WHERE user_id = %s"
            params = [user_id]

            if unread_only:
                where += " AND is_read = 0"

            # 获取通知列表
            rows = db.fetch_all(
                f"""SELECT id, type, title, message, data, is_read, created_at
                    FROM notifications
                    {where}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s""",
                (*params, per_page, offset),
            )

            # 获取总数
            count_row = db.fetch_one(
                f"SELECT COUNT(*) AS cnt FROM notifications {where}", params
            )
            total = count_row["cnt"] if count_row else 0

            # 获取未读数
            unread_row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
            unread_count = unread_row["cnt"] if unread_row else 0

            notifications = []
            for r in (rows or []):
                n = dict(r)
                if n.get("data"):
                    try:
                        n["data"] = json.loads(n["data"])
                    except Exception:
                        pass
                meta = NotificationType.METADATA.get(n.get("type"), {})
                n["icon"] = meta.get("icon", "bell")
                n["color"] = meta.get("color", "info")
                notifications.append(n)

            return {
                "success": True,
                "notifications": notifications,
                "total": total,
                "unread_count": unread_count,
                "page": page,
                "per_page": per_page,
            }

        except Exception as e:
            logger.error(f"[Notification] 查询通知失败: {e}")
            return {"success": False, "message": str(e)}

    def mark_read(self, user_id: int, notification_ids: list[int] = None) -> dict:
        """标记通知为已读"""
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            if notification_ids:
                placeholders = ",".join(["%s"] * len(notification_ids))
                db.execute(
                    f"UPDATE notifications SET is_read = 1 WHERE user_id = %s AND id IN ({placeholders})",
                    (user_id, *notification_ids),
                )
            else:
                # 全部标记已读
                db.execute(
                    "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
                    (user_id,),
                )
            return {"success": True}
        except Exception as e:
            logger.error(f"[Notification] 标记已读失败: {e}")
            return {"success": False, "message": str(e)}

    def delete_notifications(self, user_id: int, notification_ids: list[int]) -> dict:
        """删除通知"""
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            placeholders = ",".join(["%s"] * len(notification_ids))
            db.execute(
                f"DELETE FROM notifications WHERE user_id = %s AND id IN ({placeholders})",
                (user_id, *notification_ids),
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _send_email_notification(self, user_id: int, ntype: str,
                                 title: str, message: str, data: dict = None):
        """发送邮件通知"""
        try:
            db = self._get_db()
            if not db:
                return

            user = db.fetch_one("SELECT email FROM users WHERE id = %s", (user_id,))
            if not user or not user.get("email"):
                return

            from utils.email_sender import EmailSender
            meta = NotificationType.METADATA.get(ntype, {})
            color_map = {"success": "#22c55e", "danger": "#ef4444", "warning": "#f59e0b", "info": "#6366f1"}
            color = color_map.get(meta.get("color", "info"), "#6366f1")

            EmailSender.send(
                to_email=user["email"],
                subject=f"[Visionary] {title}",
                html_body=f"""
                <div style="max-width:600px;margin:0 auto;font-family:sans-serif;">
                    <div style="background:{color};color:white;padding:16px 24px;border-radius:8px 8px 0 0;">
                        <h2 style="margin:0;">{title}</h2>
                    </div>
                    <div style="padding:24px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 0 8px 8px;">
                        <p style="font-size:15px;color:#334155;">{message}</p>
                        <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0;">
                        <p style="font-size:12px;color:#94a3b8;">Amazon Visionary Sourcing Tool</p>
                    </div>
                </div>
                """,
            )
        except Exception as e:
            logger.warning(f"[Notification] 邮件通知发送失败: {e}")


# 全局实例
notifier = NotificationManager()
