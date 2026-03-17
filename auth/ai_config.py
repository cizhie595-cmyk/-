"""
Coupang 选品系统 - AI 模型动态配置管理模块

功能:
  1. 保存用户的 AI 模型配置（provider, api_key, base_url, model 等）
  2. 读取用户配置并实例化 OpenAI 兼容客户端
  3. 测试 API Key 连通性
  4. API Key 脱敏展示
"""

import os
import json
import base64
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()

# ============================================================
# 支持的 AI 服务商预设
# ============================================================
AI_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "default_base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "key_prefix": "sk-",
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
        "key_prefix": "sk-",
    },
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)",
        "default_base_url": "https://api.siliconflow.cn/v1",
        "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct",
                    "deepseek-ai/DeepSeek-R1"],
        "key_prefix": "sk-",
    },
    "zhipu": {
        "name": "智谱AI (Zhipu)",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4", "glm-4-flash"],
        "key_prefix": "",
    },
    "custom": {
        "name": "自定义 (Custom)",
        "default_base_url": "",
        "models": [],
        "key_prefix": "",
    },
}

# ============================================================
# 默认配置模板
# ============================================================
DEFAULT_AI_SETTINGS = {
    "provider": "openai",
    "api_key": "",
    "base_url": "",
    "model": "gpt-4o",
    "temperature": 0.3,
    "max_tokens": 4000,
    "configured": False,
    "last_tested_at": None,
    "test_status": None,
}


class AIConfigManager:
    """AI 模型配置管理器"""

    # ============================================================
    # 获取服务商列表（供前端下拉菜单使用）
    # ============================================================
    @staticmethod
    def get_providers() -> list[dict]:
        """
        返回所有支持的 AI 服务商信息

        :return: 服务商列表（含名称、默认URL、可选模型）
        """
        result = []
        for key, info in AI_PROVIDERS.items():
            result.append({
                "id": key,
                "name": info["name"],
                "default_base_url": info["default_base_url"],
                "models": info["models"],
            })
        return result

    # ============================================================
    # 保存用户的 AI 配置
    # ============================================================
    @staticmethod
    def save_settings(user_id: int, settings: dict) -> tuple[bool, str]:
        """
        保存用户的 AI 模型配置到数据库

        :param user_id: 用户ID
        :param settings: 配置字典 {provider, api_key, base_url, model, temperature, max_tokens}
        :return: (是否成功, 提示信息)
        """
        from database.connection import db

        provider = settings.get("provider", "openai")
        api_key = settings.get("api_key", "").strip()
        base_url = settings.get("base_url", "").strip()
        model = settings.get("model", "").strip()
        temperature = settings.get("temperature", 0.3)
        max_tokens = settings.get("max_tokens", 4000)

        # --- 参数校验 ---
        if provider not in AI_PROVIDERS:
            return False, f"不支持的服务商: {provider}，可选: {', '.join(AI_PROVIDERS.keys())}"

        if not api_key:
            return False, "API Key 不能为空"

        if not model:
            # 使用服务商的默认模型
            default_models = AI_PROVIDERS[provider]["models"]
            model = default_models[0] if default_models else "gpt-4o"

        # 如果用户没有填 base_url，使用服务商的默认值
        if not base_url:
            base_url = AI_PROVIDERS[provider]["default_base_url"]

        # 限制 temperature 范围
        try:
            temperature = max(0.0, min(2.0, float(temperature)))
        except (ValueError, TypeError):
            temperature = 0.3

        # 限制 max_tokens 范围
        try:
            max_tokens = max(100, min(128000, int(max_tokens)))
        except (ValueError, TypeError):
            max_tokens = 4000

        # --- 构建 JSON 配置 ---
        ai_settings = {
            "provider": provider,
            "api_key": AIConfigManager._encrypt_key(api_key),
            "base_url": base_url,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "configured": True,
            "updated_at": datetime.now().isoformat(),
        }

        try:
            sql = "UPDATE users SET ai_settings = %s WHERE id = %s"
            db.execute(sql, (json.dumps(ai_settings, ensure_ascii=False), user_id))

            # 同时更新旧字段（向后兼容）
            sql2 = "UPDATE users SET openai_api_key = %s, openai_model = %s WHERE id = %s"
            db.execute(sql2, (api_key, model, user_id))

            logger.info(f"AI 配置保存成功: user_id={user_id}, provider={provider}, model={model}")
            return True, "AI 模型配置保存成功"

        except Exception as e:
            logger.error(f"AI 配置保存失败: {e}")
            return False, f"保存失败: {str(e)}"

    # ============================================================
    # 读取用户的 AI 配置
    # ============================================================
    @staticmethod
    def get_settings(user_id: int) -> dict:
        """
        从数据库读取用户的 AI 配置

        :param user_id: 用户ID
        :return: 配置字典（api_key 已解密）
        """
        from database.connection import db

        try:
            sql = "SELECT ai_settings, openai_api_key, openai_model FROM users WHERE id = %s"
            row = db.fetch_one(sql, (user_id,))

            if not row:
                return dict(DEFAULT_AI_SETTINGS)

            # 优先使用新的 ai_settings JSON 字段
            if row.get("ai_settings"):
                settings = row["ai_settings"]
                if isinstance(settings, str):
                    settings = json.loads(settings)

                # 解密 api_key
                if settings.get("api_key"):
                    settings["api_key"] = AIConfigManager._decrypt_key(settings["api_key"])

                return settings

            # 兼容旧字段
            if row.get("openai_api_key"):
                return {
                    "provider": "openai",
                    "api_key": row["openai_api_key"],
                    "base_url": "",
                    "model": row.get("openai_model", "gpt-4"),
                    "temperature": 0.3,
                    "max_tokens": 4000,
                    "configured": True,
                }

        except Exception as e:
            logger.error(f"读取 AI 配置失败: {e}")

        return dict(DEFAULT_AI_SETTINGS)

    # ============================================================
    # 获取脱敏后的配置（供前端展示）
    # ============================================================
    @staticmethod
    def get_safe_settings(user_id: int) -> dict:
        """
        获取脱敏后的 AI 配置（API Key 只显示前后几位）

        :param user_id: 用户ID
        :return: 脱敏后的配置字典
        """
        settings = AIConfigManager.get_settings(user_id)

        safe = dict(settings)
        if safe.get("api_key"):
            safe["api_key_masked"] = AIConfigManager._mask_key(safe["api_key"])
        else:
            safe["api_key_masked"] = ""

        # 不返回原始 key
        safe.pop("api_key", None)

        return safe

    # ============================================================
    # 测试 API Key 连通性
    # ============================================================
    @staticmethod
    def test_connection(user_id: int = None, settings: dict = None) -> tuple[bool, str]:
        """
        测试 AI API 连通性

        可以传入 user_id（从数据库读取配置）或直接传入 settings

        :return: (是否成功, 结果信息)
        """
        if settings is None and user_id is not None:
            settings = AIConfigManager.get_settings(user_id)

        if not settings or not settings.get("api_key"):
            return False, "未配置 API Key"

        api_key = settings["api_key"]
        base_url = settings.get("base_url") or AI_PROVIDERS.get(
            settings.get("provider", "openai"), {}
        ).get("default_base_url", "https://api.openai.com/v1")
        model = settings.get("model", "gpt-4o")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url)

            # 发送一个极简的测试请求
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi, this is a connection test. Reply with OK."}],
                max_tokens=10,
                temperature=0,
            )

            reply = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else 0

            # 更新测试状态到数据库
            if user_id:
                AIConfigManager._update_test_status(user_id, True)

            result_msg = (
                f"连接成功！模型 {model} 响应正常。"
                f"回复: \"{reply}\"，消耗 {tokens_used} tokens。"
            )
            logger.info(f"AI 连接测试成功: user_id={user_id}, model={model}")
            return True, result_msg

        except ImportError:
            return False, "openai 库未安装，请运行: pip install openai"

        except Exception as e:
            error_msg = str(e)

            # 更新测试状态
            if user_id:
                AIConfigManager._update_test_status(user_id, False, error_msg)

            # 友好的错误提示
            if "401" in error_msg or "Unauthorized" in error_msg:
                return False, "API Key 无效或已过期，请检查后重新输入"
            elif "404" in error_msg:
                return False, f"模型 {model} 不存在或不可用，请检查模型名称"
            elif "429" in error_msg:
                return False, "请求频率超限，请稍后再试"
            elif "Connection" in error_msg or "timeout" in error_msg.lower():
                return False, f"无法连接到 {base_url}，请检查网络或 Base URL 是否正确"
            else:
                return False, f"连接失败: {error_msg}"

    # ============================================================
    # 根据用户配置创建 OpenAI 客户端实例
    # ============================================================
    @staticmethod
    def create_client(user_id: int):
        """
        根据用户的 AI 配置创建 OpenAI 兼容客户端

        :param user_id: 用户ID
        :return: OpenAI 客户端实例，未配置则返回 None
        """
        settings = AIConfigManager.get_settings(user_id)

        if not settings.get("api_key") or not settings.get("configured"):
            logger.warning(f"用户 {user_id} 未配置 AI 模型，AI 功能将被禁用")
            return None

        try:
            from openai import OpenAI

            api_key = settings["api_key"]
            base_url = settings.get("base_url") or AI_PROVIDERS.get(
                settings.get("provider", "openai"), {}
            ).get("default_base_url", "https://api.openai.com/v1")

            client = OpenAI(api_key=api_key, base_url=base_url)
            logger.info(
                f"AI 客户端创建成功: user_id={user_id}, "
                f"provider={settings.get('provider')}, model={settings.get('model')}"
            )
            return client

        except ImportError:
            logger.warning("openai 库未安装")
            return None
        except Exception as e:
            logger.error(f"创建 AI 客户端失败: {e}")
            return None

    # ============================================================
    # 获取用户配置的模型名称
    # ============================================================
    @staticmethod
    def get_model_name(user_id: int) -> str:
        """获取用户配置的模型名称"""
        settings = AIConfigManager.get_settings(user_id)
        return settings.get("model", "gpt-4o")

    # ============================================================
    # 内部工具方法
    # ============================================================
    @staticmethod
    def _encrypt_key(api_key: str) -> str:
        """
        简单加密 API Key（Base64 编码）

        注意: 生产环境应使用 AES-256 等强加密方式
        """
        if not api_key:
            return ""
        return base64.b64encode(api_key.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _decrypt_key(encrypted_key: str) -> str:
        """解密 API Key"""
        if not encrypted_key:
            return ""
        try:
            return base64.b64decode(encrypted_key.encode("utf-8")).decode("utf-8")
        except Exception:
            # 如果解密失败，可能是未加密的旧数据，直接返回
            return encrypted_key

    @staticmethod
    def _mask_key(api_key: str) -> str:
        """
        脱敏 API Key，只显示前6位和后4位

        示例: sk-proj-abc...wxyz
        """
        if not api_key:
            return ""
        if len(api_key) <= 12:
            return api_key[:3] + "..." + api_key[-2:]
        return api_key[:6] + "..." + api_key[-4:]

    @staticmethod
    def _update_test_status(user_id: int, success: bool, error: str = None):
        """更新数据库中的测试状态"""
        from database.connection import db

        try:
            sql = """
                UPDATE users SET ai_settings = JSON_SET(
                    COALESCE(ai_settings, '{}'),
                    '$.last_tested_at', %s,
                    '$.test_status', %s,
                    '$.test_error', %s
                ) WHERE id = %s
            """
            db.execute(sql, (
                datetime.now().isoformat(),
                "success" if success else "failed",
                error or "",
                user_id,
            ))
        except Exception as e:
            logger.error(f"更新测试状态失败: {e}")
