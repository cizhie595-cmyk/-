"""
Coupang 选品系统 - OAuth 第三方登录处理器
支持: Google OAuth 2.0, GitHub OAuth
"""

import os
import requests
from typing import Optional
from utils.logger import get_logger

logger = get_logger()


# ============================================================
# OAuth 配置
# ============================================================

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

# GitHub OAuth
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "")


class OAuthProvider:
    """OAuth 提供商基类"""

    @staticmethod
    def is_configured(provider: str) -> bool:
        """检查指定提供商是否已配置"""
        if provider == "google":
            return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
        elif provider == "github":
            return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)
        return False

    @staticmethod
    def get_available_providers() -> list:
        """获取已配置的提供商列表"""
        providers = []
        if OAuthProvider.is_configured("google"):
            providers.append({"id": "google", "name": "Google"})
        if OAuthProvider.is_configured("github"):
            providers.append({"id": "github", "name": "GitHub"})
        return providers


class GoogleOAuth:
    """Google OAuth 2.0 处理器"""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @staticmethod
    def get_auth_url(state: str = "") -> str:
        """
        生成 Google 授权 URL

        :param state: CSRF 防护 state 参数
        :return: 授权 URL
        """
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{GoogleOAuth.AUTH_URL}?{query}"

    @staticmethod
    def exchange_code(code: str) -> Optional[dict]:
        """
        用授权码换取 access_token

        :param code: 授权码
        :return: {"access_token": ..., "id_token": ..., ...} 或 None
        """
        try:
            resp = requests.post(GoogleOAuth.TOKEN_URL, data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            }, timeout=10)

            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"[GoogleOAuth] Token exchange failed: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            logger.error(f"[GoogleOAuth] Token exchange error: {e}")
            return None

    @staticmethod
    def get_user_info(access_token: str) -> Optional[dict]:
        """
        获取 Google 用户信息

        :param access_token: 访问令牌
        :return: {"id": ..., "email": ..., "name": ..., "picture": ...} 或 None
        """
        try:
            resp = requests.get(GoogleOAuth.USERINFO_URL, headers={
                "Authorization": f"Bearer {access_token}",
            }, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "provider": "google",
                    "provider_id": data.get("id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "avatar": data.get("picture"),
                    "email_verified": data.get("verified_email", False),
                }
            else:
                logger.error(f"[GoogleOAuth] Get user info failed: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"[GoogleOAuth] Get user info error: {e}")
            return None


class GitHubOAuth:
    """GitHub OAuth 处理器"""

    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USERINFO_URL = "https://api.github.com/user"
    EMAIL_URL = "https://api.github.com/user/emails"

    @staticmethod
    def get_auth_url(state: str = "") -> str:
        """生成 GitHub 授权 URL"""
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": GITHUB_REDIRECT_URI,
            "scope": "read:user user:email",
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{GitHubOAuth.AUTH_URL}?{query}"

    @staticmethod
    def exchange_code(code: str) -> Optional[dict]:
        """用授权码换取 access_token"""
        try:
            resp = requests.post(GitHubOAuth.TOKEN_URL, data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            }, headers={
                "Accept": "application/json",
            }, timeout=10)

            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"[GitHubOAuth] Token exchange failed: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"[GitHubOAuth] Token exchange error: {e}")
            return None

    @staticmethod
    def get_user_info(access_token: str) -> Optional[dict]:
        """获取 GitHub 用户信息"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            # 获取基本信息
            resp = requests.get(GitHubOAuth.USERINFO_URL, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.error(f"[GitHubOAuth] Get user info failed: {resp.status_code}")
                return None

            data = resp.json()

            # 获取邮箱（可能需要额外请求）
            email = data.get("email")
            if not email:
                email_resp = requests.get(GitHubOAuth.EMAIL_URL, headers=headers, timeout=10)
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next((e for e in emails if e.get("primary")), None)
                    if primary:
                        email = primary["email"]

            return {
                "provider": "github",
                "provider_id": str(data.get("id")),
                "email": email,
                "name": data.get("name") or data.get("login"),
                "avatar": data.get("avatar_url"),
                "email_verified": True,  # GitHub 邮箱已验证
            }
        except Exception as e:
            logger.error(f"[GitHubOAuth] Get user info error: {e}")
            return None


# ============================================================
# 统一 OAuth 入口
# ============================================================

def get_oauth_auth_url(provider: str, state: str = "") -> Optional[str]:
    """获取 OAuth 授权 URL"""
    if provider == "google" and OAuthProvider.is_configured("google"):
        return GoogleOAuth.get_auth_url(state)
    elif provider == "github" and OAuthProvider.is_configured("github"):
        return GitHubOAuth.get_auth_url(state)
    return None


def oauth_callback(provider: str, code: str) -> Optional[dict]:
    """
    处理 OAuth 回调

    :param provider: 提供商 (google/github)
    :param code: 授权码
    :return: 用户信息 dict 或 None
    """
    if provider == "google":
        token_data = GoogleOAuth.exchange_code(code)
        if not token_data or "access_token" not in token_data:
            return None
        return GoogleOAuth.get_user_info(token_data["access_token"])

    elif provider == "github":
        token_data = GitHubOAuth.exchange_code(code)
        if not token_data or "access_token" not in token_data:
            return None
        return GitHubOAuth.get_user_info(token_data["access_token"])

    return None
