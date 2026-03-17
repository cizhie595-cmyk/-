"""
Coupang 选品系统 - 密码加密与验证工具
使用 bcrypt 算法进行密码哈希
"""

import bcrypt
import re


def hash_password(plain_password: str) -> str:
    """
    对明文密码进行 bcrypt 哈希

    :param plain_password: 明文密码
    :return: 哈希后的密码字符串
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与哈希密码匹配

    :param plain_password: 明文密码
    :param hashed_password: 数据库中存储的哈希密码
    :return: 是否匹配
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度

    要求:
    - 长度至少8位
    - 包含大写字母
    - 包含小写字母
    - 包含数字
    - 包含特殊字符（可选但推荐）

    :return: (是否合格, 提示信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8位"

    if not re.search(r"[A-Z]", password):
        return False, "密码需包含至少一个大写字母"

    if not re.search(r"[a-z]", password):
        return False, "密码需包含至少一个小写字母"

    if not re.search(r"\d", password):
        return False, "密码需包含至少一个数字"

    return True, "密码强度合格"


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_username(username: str) -> tuple[bool, str]:
    """
    验证用户名格式

    要求:
    - 长度3-30位
    - 只能包含字母、数字、下划线
    - 不能以数字开头
    """
    if len(username) < 3 or len(username) > 30:
        return False, "用户名长度需在3-30位之间"

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", username):
        return False, "用户名只能包含字母、数字和下划线，且不能以数字开头"

    return True, "用户名格式合格"
