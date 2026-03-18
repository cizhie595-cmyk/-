"""
Coupang 选品系统 - 用户数据模型
封装用户表的 CRUD 操作
"""

from datetime import datetime
from typing import Optional

from database.connection import db
from auth.password import hash_password, verify_password
from utils.logger import get_logger

logger = get_logger()


class UserModel:
    """用户数据模型"""

    # ============================================================
    # 创建用户
    # ============================================================
    @staticmethod
    def create(username: str, email: str, password: str,
               nickname: str = None, role: str = "user",
               language: str = "zh_CN") -> Optional[int]:
        """
        创建新用户

        :param username: 用户名
        :param email: 邮箱
        :param password: 明文密码（会自动哈希）
        :param nickname: 昵称
        :param role: 角色
        :param language: 语言偏好
        :return: 新用户ID，失败返回 None
        """
        try:
            pwd_hash = hash_password(password)
            sql = """INSERT INTO users
                     (username, email, password_hash, nickname, role, language)
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            user_id = db.insert_and_get_id(sql, (
                username, email, pwd_hash,
                nickname or username, role, language,
            ))
            logger.info(f"用户创建成功: {username} (ID: {user_id})")
            return user_id
        except Exception as e:
            logger.error(f"用户创建失败: {e}")
            return None

    # ============================================================
    # 查询用户
    # ============================================================
    @staticmethod
    def get_by_id(user_id: int) -> Optional[dict]:
        """根据ID查询用户"""
        sql = "SELECT * FROM users WHERE id = %s AND is_active = 1"
        return db.fetch_one(sql, (user_id,))

    @staticmethod
    def get_by_username(username: str) -> Optional[dict]:
        """根据用户名查询用户"""
        sql = "SELECT * FROM users WHERE username = %s"
        return db.fetch_one(sql, (username,))

    @staticmethod
    def get_by_email(email: str) -> Optional[dict]:
        """根据邮箱查询用户"""
        sql = "SELECT * FROM users WHERE email = %s"
        return db.fetch_one(sql, (email,))

    @staticmethod
    def check_exists(username: str = None, email: str = None) -> dict:
        """
        检查用户名或邮箱是否已存在

        :return: {"username_exists": bool, "email_exists": bool}
        """
        result = {"username_exists": False, "email_exists": False}

        if username:
            user = db.fetch_one(
                "SELECT id FROM users WHERE username = %s", (username,)
            )
            result["username_exists"] = user is not None

        if email:
            user = db.fetch_one(
                "SELECT id FROM users WHERE email = %s", (email,)
            )
            result["email_exists"] = user is not None

        return result

    # ============================================================
    # 登录验证
    # ============================================================
    @staticmethod
    def authenticate(login_id: str, password: str) -> Optional[dict]:
        """
        验证用户登录

        :param login_id: 用户名或邮箱
        :param password: 明文密码
        :return: 用户信息字典（不含密码），验证失败返回 None
        """
        # 支持用户名或邮箱登录
        if "@" in login_id:
            user = UserModel.get_by_email(login_id)
        else:
            user = UserModel.get_by_username(login_id)

        if not user:
            return None

        # 检查账号是否激活
        if not user.get("is_active"):
            logger.warning(f"账号已禁用: {login_id}")
            return None

        # 验证密码
        if not verify_password(password, user["password_hash"]):
            return None

        # 返回用户信息（排除敏感字段）
        safe_user = {k: v for k, v in user.items()
                     if k not in ("password_hash", "openai_api_key",
                                  "coupang_seller_password", "naver_client_secret")}
        return safe_user

    # ============================================================
    # 更新用户信息
    # ============================================================
    @staticmethod
    def update_profile(user_id: int, data: dict) -> bool:
        """
        更新用户基本信息

        :param user_id: 用户ID
        :param data: 要更新的字段 {"nickname": ..., "phone": ..., "language": ...}
        :return: 是否成功
        """
        allowed_fields = {"nickname", "phone", "avatar_url", "language",
                          "openai_api_key", "openai_model",
                          "coupang_seller_email", "coupang_seller_password",
                          "naver_client_id", "naver_client_secret"}

        # 只允许更新白名单中的字段
        safe_data = {k: v for k, v in data.items() if k in allowed_fields}
        if not safe_data:
            return False

        try:
            set_clause = ", ".join([f"{k} = %s" for k in safe_data.keys()])
            sql = f"UPDATE users SET {set_clause} WHERE id = %s"
            db.execute(sql, (*safe_data.values(), user_id))
            logger.info(f"用户信息更新成功: ID={user_id}")
            return True
        except Exception as e:
            logger.error(f"用户信息更新失败: {e}")
            return False

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """
        修改密码

        :return: (是否成功, 提示信息)
        """
        user = db.fetch_one("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        if not user:
            return False, "用户不存在"

        if not verify_password(old_password, user["password_hash"]):
            return False, "原密码错误"

        try:
            new_hash = hash_password(new_password)
            db.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
            logger.info(f"密码修改成功: ID={user_id}")
            return True, "密码修改成功"
        except Exception as e:
            logger.error(f"密码修改失败: {e}")
            return False, "密码修改失败"

    # ============================================================
    # 登录记录
    # ============================================================
    @staticmethod
    def record_login(user_id: int, ip: str = None, user_agent: str = None,
                     status: str = "success", fail_reason: str = None):
        """记录登录日志"""
        try:
            # 更新用户表的登录信息
            if status == "success":
                db.execute(
                    """UPDATE users SET
                       last_login_at = NOW(),
                       last_login_ip = %s,
                       login_count = login_count + 1
                       WHERE id = %s""",
                    (ip, user_id),
                )

            # 插入登录日志
            db.execute(
                """INSERT INTO user_login_logs
                   (user_id, login_ip, user_agent, login_status, fail_reason)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, ip, user_agent, status, fail_reason),
            )
        except Exception as e:
            logger.error(f"记录登录日志失败: {e}")

    # ============================================================
    # 管理功能
    # ============================================================
    @staticmethod
    def list_users(page: int = 1, page_size: int = 20) -> dict:
        """
        分页查询用户列表（管理员功能）

        :return: {"users": [...], "total": int, "page": int, "page_size": int}
        """
        offset = (page - 1) * page_size

        total_row = db.fetch_one("SELECT COUNT(*) AS total FROM users")
        total = total_row["total"] if total_row else 0

        users = db.fetch_all(
            """SELECT id, username, email, nickname, role, is_active,
                      is_verified, language, last_login_at, login_count, created_at
               FROM users
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            (page_size, offset),
        )

        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def set_email_verified(user_id: int, email: str) -> bool:
        """
        设置邮箱已验证
        :param user_id: 用户ID
        :param email: 待验证的邮箱（需与用户记录匹配）
        :return: 是否成功
        """
        try:
            db.execute(
                "UPDATE users SET is_verified = 1 WHERE id = %s AND email = %s",
                (user_id, email),
            )
            logger.info(f"邮箱验证成功: ID={user_id}, email={email}")
            return True
        except Exception as e:
            logger.error(f"邮箱验证失败: {e}")
            return False

    @staticmethod
    def reset_password(user_id: int, new_password: str) -> bool:
        """
        重置密码（不需要旧密码，用于忘记密码场景）
        :param user_id: 用户ID
        :param new_password: 新密码（明文）
        :return: 是否成功
        """
        try:
            new_hash = hash_password(new_password)
            db.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
            logger.info(f"密码重置成功: ID={user_id}")
            return True
        except Exception as e:
            logger.error(f"密码重置失败: {e}")
            return False

    @staticmethod
    def set_active(user_id: int, is_active: bool) -> bool:
        """启用/禁用用户"""
        try:
            db.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (1 if is_active else 0, user_id),
            )
            return True
        except Exception:
            return False

    @staticmethod
    def set_role(user_id: int, role: str) -> bool:
        """设置用户角色"""
        if role not in ("admin", "user", "viewer"):
            return False
        try:
            db.execute(
                "UPDATE users SET role = %s WHERE id = %s",
                (role, user_id),
            )
            return True
        except Exception:
            return False
