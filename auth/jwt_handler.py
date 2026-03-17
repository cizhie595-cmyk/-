"""
Coupang 选品系统 - JWT Token 管理
提供: Token 生成、验证、刷新
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from utils.logger import get_logger

logger = get_logger()

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "coupang-selection-system-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "24"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def create_access_token(user_id: int, username: str, role: str = "user") -> str:
    """
    生成访问令牌 (Access Token)

    :param user_id: 用户ID
    :param username: 用户名
    :param role: 用户角色
    :return: JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),         # 用户ID (字符串格式)
        "username": username,        # 用户名
        "role": role,                # 角色
        "type": "access",            # Token类型
        "iat": now,                  # 签发时间
        "exp": now + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS),  # 过期时间
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def create_refresh_token(user_id: int) -> str:
    """
    生成刷新令牌 (Refresh Token)
    用于在 Access Token 过期后获取新的 Access Token

    :param user_id: 用户ID
    :return: JWT Refresh Token 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[dict]:
    """
    验证并解析 JWT Token

    :param token: JWT Token 字符串
    :return: 解析后的 payload 字典，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Token 无效: {e}")
        return None


def verify_access_token(token: str) -> Optional[dict]:
    """
    验证访问令牌

    :return: 用户信息字典 {"user_id": ..., "username": ..., "role": ...}，失败返回 None
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "access":
        return {
            "user_id": int(payload["sub"]),
            "username": payload.get("username"),
            "role": payload.get("role", "user"),
        }
    return None


def verify_refresh_token(token: str) -> Optional[int]:
    """
    验证刷新令牌

    :return: 用户ID，失败返回 None
    """
    payload = verify_token(token)
    if payload and payload.get("type") == "refresh":
        return int(payload["sub"])
    return None


def refresh_access_token(refresh_token: str, username: str, role: str) -> Optional[str]:
    """
    使用 Refresh Token 刷新 Access Token

    :param refresh_token: 刷新令牌
    :param username: 用户名（需要从数据库获取最新的）
    :param role: 用户角色
    :return: 新的 Access Token，失败返回 None
    """
    user_id = verify_refresh_token(refresh_token)
    if user_id:
        return create_access_token(user_id, username, role)
    return None
