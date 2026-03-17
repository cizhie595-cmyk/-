"""
第三方 API 密钥统一配置管理模块

管理系统中所有需要用户自行配置的第三方 API 密钥：
  - Amazon SP-API（卖家中心 API）
  - Keepa API（历史价格和 BSR 数据）
  - Rainforest API（Amazon 数据抓取）
  - Meshy AI（3D 模型生成）
  - Tripo AI（3D 模型生成）
  - Google Trends（趋势数据，通过 SerpAPI）
  - 1688 开放平台 API

每个服务的密钥独立存储、独立加密、独立测试。
"""

import json
import base64
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 支持的第三方服务定义
# ============================================================

THIRD_PARTY_SERVICES = {
    "amazon_sp_api": {
        "name": "Amazon SP-API",
        "description": "Amazon 卖家中心 API，用于获取销售数据、搜索词报告等",
        "fields": [
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "required": True},
            {"key": "lwa_app_id", "label": "LWA App ID (Client ID)", "type": "text", "required": True},
            {"key": "lwa_client_secret", "label": "LWA Client Secret", "type": "password", "required": True},
            {"key": "aws_access_key", "label": "AWS Access Key", "type": "text", "required": True},
            {"key": "aws_secret_key", "label": "AWS Secret Key", "type": "password", "required": True},
            {"key": "role_arn", "label": "Role ARN", "type": "text", "required": False},
            {"key": "marketplace_id", "label": "Marketplace ID", "type": "text", "required": True,
             "default": "ATVPDKIKX0DER", "help": "US: ATVPDKIKX0DER, UK: A1F83G8C2ARO7P, DE: A1PA6795UKMFR9"},
        ],
        "doc_url": "https://developer-docs.amazon.com/sp-api/",
        "test_endpoint": "https://sellingpartnerapi-na.amazon.com",
    },
    "keepa": {
        "name": "Keepa API",
        "description": "Amazon 历史价格、BSR 排名、销量预估数据",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "required": True},
        ],
        "doc_url": "https://keepa.com/#!discuss/t/using-the-keepa-api/47",
        "test_endpoint": "https://api.keepa.com/token",
        "pricing": "按 Token 计费，$19/月起",
    },
    "rainforest": {
        "name": "Rainforest API",
        "description": "Amazon 产品数据、搜索结果、评论数据 API",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "required": True},
        ],
        "doc_url": "https://www.rainforestapi.com/docs",
        "test_endpoint": "https://api.rainforestapi.com/request",
        "pricing": "按请求计费，$49/月起",
    },
    "meshy": {
        "name": "Meshy AI",
        "description": "AI 3D 模型生成（图片转3D、文字转3D）",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "required": True},
        ],
        "doc_url": "https://docs.meshy.ai/",
        "test_endpoint": "https://api.meshy.ai/v2/image-to-3d",
        "pricing": "免费额度 + 按量计费",
    },
    "tripo": {
        "name": "Tripo AI",
        "description": "高精度 AI 3D 模型生成",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "required": True},
        ],
        "doc_url": "https://platform.tripo3d.ai/docs",
        "test_endpoint": "https://api.tripo3d.ai/v2/openapi/task",
        "pricing": "免费额度 + 按量计费",
    },
    "serpapi": {
        "name": "SerpAPI (Google Trends)",
        "description": "通过 SerpAPI 获取 Google Trends 趋势数据",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "required": True},
        ],
        "doc_url": "https://serpapi.com/google-trends-api",
        "test_endpoint": "https://serpapi.com/account",
        "pricing": "免费100次/月，$50/月起",
    },
    "alibaba_1688": {
        "name": "1688 开放平台",
        "description": "1688 货源搜索和供应商数据",
        "fields": [
            {"key": "app_key", "label": "App Key", "type": "text", "required": True},
            {"key": "app_secret", "label": "App Secret", "type": "password", "required": True},
        ],
        "doc_url": "https://open.1688.com/",
        "pricing": "免费申请",
    },
}


class APIKeysConfigManager:
    """
    第三方 API 密钥统一配置管理器

    所有密钥存储在 users 表的 api_keys_settings JSON 字段中。
    """

    @staticmethod
    def get_services() -> list[dict]:
        """
        获取所有支持的第三方服务列表（供前端展示）。

        :return: 服务列表
        """
        result = []
        for service_id, info in THIRD_PARTY_SERVICES.items():
            result.append({
                "id": service_id,
                "name": info["name"],
                "description": info["description"],
                "fields": info["fields"],
                "doc_url": info.get("doc_url", ""),
                "pricing": info.get("pricing", ""),
            })
        return result

    @staticmethod
    def save_service_config(user_id: int, service_id: str, config: dict) -> tuple[bool, str]:
        """
        保存某个第三方服务的配置。

        :param user_id: 用户 ID
        :param service_id: 服务 ID（如 keepa, meshy 等）
        :param config: 配置字典
        :return: (是否成功, 提示信息)
        """
        if service_id not in THIRD_PARTY_SERVICES:
            return False, f"不支持的服务: {service_id}"

        service_def = THIRD_PARTY_SERVICES[service_id]

        # 验证必填字段
        for field in service_def["fields"]:
            if field["required"] and not config.get(field["key"], "").strip():
                return False, f"缺少必填字段: {field['label']}"

        # 加密密码类型的字段
        encrypted_config = {}
        for field in service_def["fields"]:
            value = config.get(field["key"], "").strip()
            if field["type"] == "password" and value:
                encrypted_config[field["key"]] = _encrypt(value)
            else:
                encrypted_config[field["key"]] = value

        encrypted_config["configured"] = True
        encrypted_config["updated_at"] = datetime.now().isoformat()

        # 读取现有配置
        from database.connection import db

        try:
            sql = "SELECT api_keys_settings FROM users WHERE id = %s"
            row = db.fetch_one(sql, (user_id,))

            all_settings = {}
            if row and row.get("api_keys_settings"):
                raw = row["api_keys_settings"]
                all_settings = json.loads(raw) if isinstance(raw, str) else raw

            all_settings[service_id] = encrypted_config

            # 保存回数据库
            sql = "UPDATE users SET api_keys_settings = %s WHERE id = %s"
            db.execute(sql, (json.dumps(all_settings, ensure_ascii=False), user_id))

            logger.info(f"[API Keys] 保存成功: user_id={user_id}, service={service_id}")
            return True, f"{service_def['name']} 配置保存成功"

        except Exception as e:
            logger.error(f"[API Keys] 保存失败: {e}")
            return False, f"保存失败: {str(e)}"

    @staticmethod
    def get_service_config(user_id: int, service_id: str,
                            decrypt: bool = True) -> dict:
        """
        获取某个第三方服务的配置。

        :param user_id: 用户 ID
        :param service_id: 服务 ID
        :param decrypt: 是否解密密码字段
        :return: 配置字典
        """
        from database.connection import db

        try:
            sql = "SELECT api_keys_settings FROM users WHERE id = %s"
            row = db.fetch_one(sql, (user_id,))

            if not row or not row.get("api_keys_settings"):
                return {"configured": False}

            raw = row["api_keys_settings"]
            all_settings = json.loads(raw) if isinstance(raw, str) else raw

            config = all_settings.get(service_id, {"configured": False})

            if decrypt and service_id in THIRD_PARTY_SERVICES:
                service_def = THIRD_PARTY_SERVICES[service_id]
                for field in service_def["fields"]:
                    if field["type"] == "password" and config.get(field["key"]):
                        config[field["key"]] = _decrypt(config[field["key"]])

            return config

        except Exception as e:
            logger.error(f"[API Keys] 读取失败: {e}")
            return {"configured": False}

    @staticmethod
    def get_safe_config(user_id: int, service_id: str) -> dict:
        """
        获取脱敏后的配置（供前端展示）。
        """
        config = APIKeysConfigManager.get_service_config(user_id, service_id, decrypt=True)

        safe = dict(config)
        if service_id in THIRD_PARTY_SERVICES:
            service_def = THIRD_PARTY_SERVICES[service_id]
            for field in service_def["fields"]:
                if field["type"] == "password" and safe.get(field["key"]):
                    safe[field["key"] + "_masked"] = _mask(safe[field["key"]])
                    safe.pop(field["key"], None)

        return safe

    @staticmethod
    def get_all_configs_safe(user_id: int) -> dict:
        """
        获取所有服务的脱敏配置（供前端设置页面一次性加载）。
        """
        result = {}
        for service_id in THIRD_PARTY_SERVICES:
            result[service_id] = APIKeysConfigManager.get_safe_config(user_id, service_id)
        return result

    @staticmethod
    def test_service(user_id: int, service_id: str) -> tuple[bool, str]:
        """
        测试某个第三方服务的连通性。

        :param user_id: 用户 ID
        :param service_id: 服务 ID
        :return: (是否成功, 结果信息)
        """
        config = APIKeysConfigManager.get_service_config(user_id, service_id, decrypt=True)

        if not config.get("configured"):
            return False, "该服务尚未配置"

        import requests

        try:
            if service_id == "keepa":
                resp = requests.get(
                    "https://api.keepa.com/token",
                    params={"key": config["api_key"]},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("tokensLeft", 0)
                    return True, f"Keepa 连接成功！剩余 Token: {tokens}"
                else:
                    return False, f"Keepa API Key 无效 (HTTP {resp.status_code})"

            elif service_id == "rainforest":
                resp = requests.get(
                    "https://api.rainforestapi.com/request",
                    params={"api_key": config["api_key"], "type": "account"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return True, "Rainforest API 连接成功！"
                else:
                    return False, f"Rainforest API Key 无效 (HTTP {resp.status_code})"

            elif service_id == "meshy":
                resp = requests.get(
                    "https://api.meshy.ai/v2/image-to-3d",
                    headers={"Authorization": f"Bearer {config['api_key']}"},
                    params={"limit": 1},
                    timeout=10,
                )
                if resp.status_code in (200, 404):
                    return True, "Meshy AI 连接成功！"
                elif resp.status_code == 401:
                    return False, "Meshy API Key 无效"
                else:
                    return False, f"Meshy 连接异常 (HTTP {resp.status_code})"

            elif service_id == "tripo":
                resp = requests.get(
                    "https://api.tripo3d.ai/v2/openapi/task",
                    headers={"Authorization": f"Bearer {config['api_key']}"},
                    params={"page_num": 1, "page_size": 1},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return True, "Tripo AI 连接成功！"
                elif resp.status_code == 401:
                    return False, "Tripo API Key 无效"
                else:
                    return False, f"Tripo 连接异常 (HTTP {resp.status_code})"

            elif service_id == "serpapi":
                resp = requests.get(
                    "https://serpapi.com/account",
                    params={"api_key": config["api_key"]},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    searches = data.get("total_searches_left", 0)
                    return True, f"SerpAPI 连接成功！剩余搜索次数: {searches}"
                else:
                    return False, f"SerpAPI Key 无效 (HTTP {resp.status_code})"

            elif service_id == "amazon_sp_api":
                # SP-API 测试需要获取 access_token
                resp = requests.post(
                    "https://api.amazon.com/auth/o2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": config.get("refresh_token", ""),
                        "client_id": config.get("lwa_app_id", ""),
                        "client_secret": config.get("lwa_client_secret", ""),
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    return True, "Amazon SP-API 认证成功！"
                else:
                    return False, f"SP-API 认证失败: {resp.text[:200]}"

            elif service_id == "alibaba_1688":
                return True, "1688 配置已保存（连通性需在实际调用时验证）"

            else:
                return False, f"暂不支持 {service_id} 的连通性测试"

        except requests.exceptions.Timeout:
            return False, "连接超时，请检查网络"
        except requests.exceptions.ConnectionError:
            return False, "无法连接到服务器，请检查网络"
        except Exception as e:
            return False, f"测试失败: {str(e)}"

    @staticmethod
    def delete_service_config(user_id: int, service_id: str) -> tuple[bool, str]:
        """删除某个服务的配置"""
        from database.connection import db

        try:
            sql = "SELECT api_keys_settings FROM users WHERE id = %s"
            row = db.fetch_one(sql, (user_id,))

            if not row or not row.get("api_keys_settings"):
                return True, "配置不存在"

            raw = row["api_keys_settings"]
            all_settings = json.loads(raw) if isinstance(raw, str) else raw

            if service_id in all_settings:
                del all_settings[service_id]

            sql = "UPDATE users SET api_keys_settings = %s WHERE id = %s"
            db.execute(sql, (json.dumps(all_settings, ensure_ascii=False), user_id))

            return True, "配置已删除"

        except Exception as e:
            logger.error(f"[API Keys] 删除失败: {e}")
            return False, f"删除失败: {str(e)}"


# ============================================================
# 加密/解密/脱敏工具函数
# ============================================================

def _encrypt(value: str) -> str:
    """Base64 加密（生产环境应使用 AES-256）"""
    if not value:
        return ""
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def _decrypt(encrypted: str) -> str:
    """Base64 解密"""
    if not encrypted:
        return ""
    try:
        return base64.b64decode(encrypted.encode("utf-8")).decode("utf-8")
    except Exception:
        return encrypted


def _mask(value: str) -> str:
    """脱敏显示"""
    if not value:
        return ""
    if len(value) <= 8:
        return value[:2] + "***" + value[-1:]
    return value[:4] + "***" + value[-4:]
