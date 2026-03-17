"""
Coupang 选品系统 - 多语言国际化模块 (i18n)
支持: 简体中文(zh_CN) / English(en_US) / 한국어(ko_KR)
"""

import os
import json
from typing import Optional

# 语言包目录
LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "1": "zh_CN",
    "2": "en_US",
    "3": "ko_KR",
}

LANGUAGE_NAMES = {
    "zh_CN": "简体中文",
    "en_US": "English",
    "ko_KR": "한국어",
}


class I18n:
    """
    国际化翻译引擎
    用法:
        from i18n import t, set_language
        set_language("zh_CN")
        print(t("common.welcome"))
        print(t("crawler.found_products", count=50))
    """

    _instance = None
    _locale_data: dict = {}
    _current_lang: str = "zh_CN"
    _fallback_lang: str = "en_US"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all_locales()
        return cls._instance

    def _load_all_locales(self):
        """加载所有语言包"""
        for lang_code in LANGUAGE_NAMES:
            filepath = os.path.join(LOCALES_DIR, f"{lang_code}.json")
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    self._locale_data[lang_code] = json.load(f)

    def set_language(self, lang_code: str) -> bool:
        """
        设置当前语言
        :param lang_code: 语言代码 (zh_CN / en_US / ko_KR)
        :return: 是否设置成功
        """
        if lang_code in self._locale_data:
            self._current_lang = lang_code
            # 保存语言偏好到配置文件
            self._save_preference(lang_code)
            return True
        return False

    def get_language(self) -> str:
        """获取当前语言代码"""
        return self._current_lang

    def get_language_name(self) -> str:
        """获取当前语言名称"""
        return LANGUAGE_NAMES.get(self._current_lang, "Unknown")

    def translate(self, key: str, **kwargs) -> str:
        """
        翻译指定的键
        :param key: 翻译键，格式为 "section.key"，如 "common.welcome"
        :param kwargs: 用于格式化的参数，如 count=50
        :return: 翻译后的文本
        """
        # 尝试当前语言
        text = self._get_text(self._current_lang, key)
        # 回退到默认语言
        if text is None:
            text = self._get_text(self._fallback_lang, key)
        # 仍然找不到，返回键名
        if text is None:
            return f"[{key}]"

        # 格式化参数
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text

    def _get_text(self, lang_code: str, key: str) -> Optional[str]:
        """从语言包中获取文本"""
        data = self._locale_data.get(lang_code, {})
        parts = key.split(".")
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                return None
        return data if isinstance(data, str) else None

    def _save_preference(self, lang_code: str):
        """保存语言偏好到本地文件"""
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        os.makedirs(config_dir, exist_ok=True)
        pref_file = os.path.join(config_dir, ".language")
        try:
            with open(pref_file, "w") as f:
                f.write(lang_code)
        except Exception:
            pass

    def load_preference(self) -> str:
        """从本地文件加载语言偏好"""
        pref_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", ".language"
        )
        try:
            if os.path.exists(pref_file):
                with open(pref_file, "r") as f:
                    lang = f.read().strip()
                    if lang in self._locale_data:
                        self._current_lang = lang
                        return lang
        except Exception:
            pass
        return self._current_lang


# ============================================================
# 全局快捷函数
# ============================================================

_i18n = I18n()
_i18n.load_preference()


def t(key: str, **kwargs) -> str:
    """
    全局翻译函数（快捷方式）
    用法: t("common.welcome") 或 t("crawler.found_products", count=50)
    """
    return _i18n.translate(key, **kwargs)


def set_language(lang_code: str) -> bool:
    """设置全局语言"""
    return _i18n.set_language(lang_code)


def get_language() -> str:
    """获取当前语言代码"""
    return _i18n.get_language()


def get_language_name() -> str:
    """获取当前语言名称"""
    return _i18n.get_language_name()


def select_language_interactive() -> str:
    """
    交互式语言选择（用于首次启动或切换语言）
    """
    print()
    print("=" * 50)
    print(t("common.select_language"))
    print("=" * 50)
    print("  1. 简体中文")
    print("  2. English")
    print("  3. 한국어")
    print("=" * 50)

    while True:
        choice = input("> ").strip()
        if choice in SUPPORTED_LANGUAGES:
            lang_code = SUPPORTED_LANGUAGES[choice]
            set_language(lang_code)
            print(f"\n✓ {LANGUAGE_NAMES[lang_code]}")
            return lang_code
        else:
            print("  1 / 2 / 3")
