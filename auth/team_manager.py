"""
Coupang 选品系统 - 团队协作与多用户权限管理
支持: 团队创建/邀请/角色管理/权限控制
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 角色与权限定义
# ============================================================

class Role:
    """角色常量"""
    OWNER = "owner"          # 团队拥有者（全部权限）
    ADMIN = "admin"          # 管理员（管理成员 + 全部业务权限）
    ANALYST = "analyst"      # 分析师（查看/分析/导出）
    VIEWER = "viewer"        # 只读（仅查看）

    ALL = [OWNER, ADMIN, ANALYST, VIEWER]

    LABELS = {
        OWNER: "拥有者",
        ADMIN: "管理员",
        ANALYST: "分析师",
        VIEWER: "只读成员",
    }


class Permission:
    """权限常量"""
    # 项目权限
    PROJECT_CREATE = "project:create"
    PROJECT_VIEW = "project:view"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    PROJECT_SCRAPE = "project:scrape"

    # 分析权限
    ANALYSIS_RUN = "analysis:run"
    ANALYSIS_VIEW = "analysis:view"
    ANALYSIS_EXPORT = "analysis:export"

    # 3D Lab 权限
    THREED_GENERATE = "3d:generate"
    THREED_VIEW = "3d:view"

    # 团队管理权限
    TEAM_MANAGE = "team:manage"
    TEAM_INVITE = "team:invite"
    TEAM_REMOVE = "team:remove"

    # 设置权限
    SETTINGS_API_KEYS = "settings:api_keys"
    SETTINGS_AI = "settings:ai"
    SETTINGS_BILLING = "settings:billing"


# 角色 -> 权限映射
ROLE_PERMISSIONS = {
    Role.OWNER: [
        Permission.PROJECT_CREATE, Permission.PROJECT_VIEW, Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE, Permission.PROJECT_SCRAPE,
        Permission.ANALYSIS_RUN, Permission.ANALYSIS_VIEW, Permission.ANALYSIS_EXPORT,
        Permission.THREED_GENERATE, Permission.THREED_VIEW,
        Permission.TEAM_MANAGE, Permission.TEAM_INVITE, Permission.TEAM_REMOVE,
        Permission.SETTINGS_API_KEYS, Permission.SETTINGS_AI, Permission.SETTINGS_BILLING,
    ],
    Role.ADMIN: [
        Permission.PROJECT_CREATE, Permission.PROJECT_VIEW, Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE, Permission.PROJECT_SCRAPE,
        Permission.ANALYSIS_RUN, Permission.ANALYSIS_VIEW, Permission.ANALYSIS_EXPORT,
        Permission.THREED_GENERATE, Permission.THREED_VIEW,
        Permission.TEAM_INVITE, Permission.TEAM_REMOVE,
        Permission.SETTINGS_API_KEYS, Permission.SETTINGS_AI,
    ],
    Role.ANALYST: [
        Permission.PROJECT_CREATE, Permission.PROJECT_VIEW, Permission.PROJECT_EDIT,
        Permission.PROJECT_SCRAPE,
        Permission.ANALYSIS_RUN, Permission.ANALYSIS_VIEW, Permission.ANALYSIS_EXPORT,
        Permission.THREED_GENERATE, Permission.THREED_VIEW,
    ],
    Role.VIEWER: [
        Permission.PROJECT_VIEW,
        Permission.ANALYSIS_VIEW,
        Permission.THREED_VIEW,
    ],
}


def has_permission(role: str, permission: str) -> bool:
    """检查角色是否拥有指定权限"""
    return permission in ROLE_PERMISSIONS.get(role, [])


def get_permissions(role: str) -> list:
    """获取角色的所有权限"""
    return ROLE_PERMISSIONS.get(role, [])


# ============================================================
# 团队管理器
# ============================================================

class TeamManager:
    """团队管理器"""

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

    def create_team(self, owner_id: int, name: str, description: str = "") -> dict:
        """
        创建团队

        :param owner_id: 创建者用户ID
        :param name: 团队名称
        :param description: 团队描述
        :return: 团队信息 dict
        """
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            invite_code = secrets.token_urlsafe(16)
            team_id = db.insert_and_get_id(
                """INSERT INTO teams (name, description, owner_id, invite_code, created_at)
                   VALUES (%s, %s, %s, %s, NOW())""",
                (name, description, owner_id, invite_code),
            )

            # 将创建者添加为 owner
            db.execute(
                """INSERT INTO team_members (team_id, user_id, role, joined_at)
                   VALUES (%s, %s, %s, NOW())""",
                (team_id, owner_id, Role.OWNER),
            )

            logger.info(f"[Team] 创建团队: id={team_id}, name={name}, owner={owner_id}")
            return {
                "success": True,
                "team": {
                    "id": team_id,
                    "name": name,
                    "description": description,
                    "invite_code": invite_code,
                    "owner_id": owner_id,
                },
            }
        except Exception as e:
            logger.error(f"[Team] 创建团队失败: {e}")
            return {"success": False, "message": str(e)}

    def invite_member(self, team_id: int, inviter_id: int,
                      email: str, role: str = Role.ANALYST) -> dict:
        """
        邀请成员加入团队

        :param team_id: 团队ID
        :param inviter_id: 邀请人ID
        :param email: 被邀请人邮箱
        :param role: 分配角色
        :return: 邀请结果
        """
        if role not in Role.ALL or role == Role.OWNER:
            return {"success": False, "message": "无效的角色"}

        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            # 检查邀请人权限
            inviter = db.fetch_one(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, inviter_id),
            )
            if not inviter or not has_permission(inviter["role"], Permission.TEAM_INVITE):
                return {"success": False, "message": "无邀请权限"}

            # 生成邀请 token
            token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(days=7)

            db.execute(
                """INSERT INTO team_invitations
                   (team_id, email, role, token, inviter_id, expires_at, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                (team_id, email, role, token, inviter_id, expires),
            )

            # 发送邀请邮件
            try:
                from utils.email_sender import EmailSender
                app_url = os.getenv("APP_FRONTEND_URL", "http://localhost:5000")
                invite_link = f"{app_url}/team/join?token={token}"

                team = db.fetch_one("SELECT name FROM teams WHERE id = %s", (team_id,))
                team_name = team["name"] if team else "Unknown"

                EmailSender.send(
                    to_email=email,
                    subject=f"邀请您加入团队 {team_name}",
                    html_body=f"""
                    <h2>团队邀请</h2>
                    <p>您被邀请加入团队 <strong>{team_name}</strong>，角色为 <strong>{Role.LABELS.get(role, role)}</strong>。</p>
                    <p><a href="{invite_link}" style="padding:10px 20px;background:#6366f1;color:white;text-decoration:none;border-radius:6px;">接受邀请</a></p>
                    <p>此链接 7 天内有效。</p>
                    """,
                )
            except Exception as e:
                logger.warning(f"[Team] 邀请邮件发送失败: {e}")

            logger.info(f"[Team] 邀请成员: team={team_id}, email={email}, role={role}")
            return {"success": True, "message": "邀请已发送", "token": token}

        except Exception as e:
            logger.error(f"[Team] 邀请失败: {e}")
            return {"success": False, "message": str(e)}

    def accept_invitation(self, token: str, user_id: int) -> dict:
        """接受团队邀请"""
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            invite = db.fetch_one(
                """SELECT * FROM team_invitations
                   WHERE token = %s AND accepted = 0 AND expires_at > NOW()""",
                (token,),
            )
            if not invite:
                return {"success": False, "message": "邀请无效或已过期"}

            # 检查是否已是成员
            existing = db.fetch_one(
                "SELECT id FROM team_members WHERE team_id = %s AND user_id = %s",
                (invite["team_id"], user_id),
            )
            if existing:
                return {"success": False, "message": "您已是该团队成员"}

            # 添加成员
            db.execute(
                """INSERT INTO team_members (team_id, user_id, role, joined_at)
                   VALUES (%s, %s, %s, NOW())""",
                (invite["team_id"], user_id, invite["role"]),
            )

            # 标记邀请已接受
            db.execute(
                "UPDATE team_invitations SET accepted = 1 WHERE id = %s",
                (invite["id"],),
            )

            return {"success": True, "message": "已加入团队"}

        except Exception as e:
            logger.error(f"[Team] 接受邀请失败: {e}")
            return {"success": False, "message": str(e)}

    def get_team_members(self, team_id: int, requester_id: int) -> dict:
        """获取团队成员列表"""
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            # 验证请求者是团队成员
            member = db.fetch_one(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, requester_id),
            )
            if not member:
                return {"success": False, "message": "非团队成员"}

            members = db.fetch_all(
                """SELECT tm.user_id, tm.role, tm.joined_at,
                          u.username, u.email
                   FROM team_members tm
                   JOIN users u ON tm.user_id = u.id
                   WHERE tm.team_id = %s
                   ORDER BY FIELD(tm.role, 'owner', 'admin', 'analyst', 'viewer'), tm.joined_at""",
                (team_id,),
            )

            return {
                "success": True,
                "members": [dict(m) for m in members] if members else [],
            }

        except Exception as e:
            logger.error(f"[Team] 获取成员失败: {e}")
            return {"success": False, "message": str(e)}

    def update_member_role(self, team_id: int, operator_id: int,
                           target_user_id: int, new_role: str) -> dict:
        """更新成员角色"""
        if new_role not in Role.ALL or new_role == Role.OWNER:
            return {"success": False, "message": "无效的角色"}

        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            operator = db.fetch_one(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, operator_id),
            )
            if not operator or not has_permission(operator["role"], Permission.TEAM_MANAGE):
                return {"success": False, "message": "无权限修改角色"}

            target = db.fetch_one(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, target_user_id),
            )
            if not target:
                return {"success": False, "message": "目标用户不是团队成员"}
            if target["role"] == Role.OWNER:
                return {"success": False, "message": "不能修改拥有者角色"}

            db.execute(
                "UPDATE team_members SET role = %s WHERE team_id = %s AND user_id = %s",
                (new_role, team_id, target_user_id),
            )

            return {"success": True, "message": f"角色已更新为 {Role.LABELS.get(new_role, new_role)}"}

        except Exception as e:
            logger.error(f"[Team] 更新角色失败: {e}")
            return {"success": False, "message": str(e)}

    def remove_member(self, team_id: int, operator_id: int, target_user_id: int) -> dict:
        """移除团队成员"""
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            operator = db.fetch_one(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, operator_id),
            )
            if not operator or not has_permission(operator["role"], Permission.TEAM_REMOVE):
                return {"success": False, "message": "无权限移除成员"}

            target = db.fetch_one(
                "SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, target_user_id),
            )
            if not target:
                return {"success": False, "message": "目标用户不是团队成员"}
            if target["role"] == Role.OWNER:
                return {"success": False, "message": "不能移除拥有者"}

            db.execute(
                "DELETE FROM team_members WHERE team_id = %s AND user_id = %s",
                (team_id, target_user_id),
            )

            return {"success": True, "message": "成员已移除"}

        except Exception as e:
            logger.error(f"[Team] 移除成员失败: {e}")
            return {"success": False, "message": str(e)}


# 全局实例
team_mgr = TeamManager()
