"""
Coupang 选品系统 - 前端国际化 API 路由
端点:
    GET  /api/i18n/<lang>       获取指定语言包
    POST /api/i18n/preference   保存用户语言偏好
    GET  /api/i18n/languages    获取支持的语言列表
"""

import os
import json
from flask import Blueprint, request, jsonify

i18n_bp = Blueprint("i18n_api", __name__, url_prefix="/api/i18n")

LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "i18n", "locales",
)

SUPPORTED_LANGUAGES = {
    "zh_CN": {"label": "简体中文", "flag": "🇨🇳"},
    "en_US": {"label": "English", "flag": "🇺🇸"},
    "ko_KR": {"label": "한국어", "flag": "🇰🇷"},
}

# 缓存语言包
_locale_cache = {}


def _load_ui_locale(lang: str) -> dict:
    """加载前端 UI 语言包"""
    if lang in _locale_cache:
        return _locale_cache[lang]

    filepath = os.path.join(LOCALES_DIR, f"ui_{lang}.json")
    if not os.path.exists(filepath):
        # 回退到 en_US
        filepath = os.path.join(LOCALES_DIR, "ui_en_US.json")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            _locale_cache[lang] = data
            return data
    except Exception:
        return {}


@i18n_bp.route("/<lang>", methods=["GET"])
def get_locale(lang):
    """获取指定语言的前端 UI 语言包"""
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en_US"

    data = _load_ui_locale(lang)
    return jsonify(data), 200


@i18n_bp.route("/preference", methods=["POST"])
def save_preference():
    """保存用户语言偏好"""
    data = request.get_json(silent=True) or {}
    language = data.get("language", "en_US")

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"success": False, "message": "不支持的语言"}), 400

    # 如果用户已登录，保存到数据库
    try:
        from auth.middleware import get_current_user
        user = get_current_user()
        if user:
            from database.connection import db
            user_id = user.get("user_id") or user.get("sub")
            db.execute(
                "UPDATE users SET language = %s WHERE id = %s",
                (language, user_id),
            )
    except Exception:
        pass

    return jsonify({"success": True, "language": language}), 200


@i18n_bp.route("/languages", methods=["GET"])
def list_languages():
    """获取支持的语言列表"""
    languages = []
    for code, info in SUPPORTED_LANGUAGES.items():
        languages.append({
            "code": code,
            "label": info["label"],
            "flag": info["flag"],
        })
    return jsonify({"success": True, "languages": languages}), 200
