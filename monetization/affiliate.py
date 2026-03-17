"""
隐性返佣机制 - Affiliate Tag 静默植入

当用户通过系统查看 Amazon 商品详情页时，自动在链接中植入
Affiliate Tag（Amazon Associates Tag），实现被动收入。

支持平台：
  - Amazon US / UK / DE / JP / CA 等多站点
  - Coupang Partners（韩国站）

实现方式：
  - 所有导出的商品链接自动附带 tag
  - 前端跳转链接自动改写
  - 报告中的链接自动植入
"""

import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from utils.logger import get_logger

logger = get_logger()


# ============================================================
# Amazon Associates Tag 配置
# ============================================================

AMAZON_AFFILIATE_CONFIG = {
    "US": {
        "domain": "amazon.com",
        "tag_param": "tag",
        "default_tag": "",  # 系统运营方的 Tag，由管理员在后台配置
    },
    "UK": {
        "domain": "amazon.co.uk",
        "tag_param": "tag",
        "default_tag": "",
    },
    "DE": {
        "domain": "amazon.de",
        "tag_param": "tag",
        "default_tag": "",
    },
    "JP": {
        "domain": "amazon.co.jp",
        "tag_param": "tag",
        "default_tag": "",
    },
    "CA": {
        "domain": "amazon.ca",
        "tag_param": "tag",
        "default_tag": "",
    },
}

COUPANG_AFFILIATE_CONFIG = {
    "domain": "coupang.com",
    "tag_param": "subid",
    "default_tag": "",
}


class AffiliateManager:
    """
    Affiliate 返佣管理器

    负责：
      1. 在 Amazon/Coupang 链接中植入 Affiliate Tag
      2. 管理系统级和用户级 Tag
      3. 追踪点击和转化
    """

    def __init__(self):
        self.system_tags = {}   # 系统级 Tag（平台运营方收入）
        self.user_tags = {}     # 用户级 Tag（可选，用户自己的 Associates 账号）
        self._load_system_tags()

    def _load_system_tags(self):
        """从数据库或环境变量加载系统级 Affiliate Tag"""
        import os

        # 优先从环境变量加载
        self.system_tags = {
            "amazon_us": os.getenv("AFFILIATE_TAG_AMAZON_US", ""),
            "amazon_uk": os.getenv("AFFILIATE_TAG_AMAZON_UK", ""),
            "amazon_de": os.getenv("AFFILIATE_TAG_AMAZON_DE", ""),
            "amazon_jp": os.getenv("AFFILIATE_TAG_AMAZON_JP", ""),
            "amazon_ca": os.getenv("AFFILIATE_TAG_AMAZON_CA", ""),
            "coupang": os.getenv("AFFILIATE_TAG_COUPANG", ""),
        }

        # 尝试从数据库加载（覆盖环境变量）
        try:
            from database.connection import db
            sql = "SELECT config_key, config_value FROM system_config WHERE config_key LIKE 'affiliate_tag_%'"
            rows = db.fetch_all(sql)
            for row in rows:
                key = row["config_key"].replace("affiliate_tag_", "")
                self.system_tags[key] = row["config_value"]
        except Exception:
            pass  # 数据库未初始化时静默跳过

    def inject_tag(self, url: str, marketplace: str = "US",
                    user_tag: str = None) -> str:
        """
        在商品链接中植入 Affiliate Tag。

        优先级：用户自己的 Tag > 系统 Tag

        :param url: 原始商品链接
        :param marketplace: 站点（US/UK/DE/JP/CA/COUPANG）
        :param user_tag: 用户自定义的 Affiliate Tag（可选）
        :return: 植入 Tag 后的链接
        """
        if not url:
            return url

        # 确定使用哪个 Tag
        tag = user_tag or self._get_system_tag(marketplace)
        if not tag:
            return url  # 没有配置 Tag，返回原链接

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)

            # 确定 Tag 参数名
            if marketplace.upper() == "COUPANG":
                tag_param = COUPANG_AFFILIATE_CONFIG["tag_param"]
            else:
                tag_param = "tag"

            # 植入或替换 Tag
            params[tag_param] = [tag]

            # 重建 URL
            new_query = urlencode(params, doseq=True)
            new_url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))

            return new_url

        except Exception as e:
            logger.error(f"[Affiliate] Tag 植入失败: {e}")
            return url

    def inject_tags_batch(self, products: list[dict],
                           marketplace: str = "US",
                           user_tag: str = None) -> list[dict]:
        """
        批量为产品列表中的链接植入 Affiliate Tag。

        :param products: 产品列表
        :param marketplace: 站点
        :param user_tag: 用户 Tag
        :return: 处理后的产品列表
        """
        for product in products:
            # 处理主链接
            if product.get("url"):
                product["url"] = self.inject_tag(product["url"], marketplace, user_tag)

            # 处理详情页链接
            if product.get("detail_url"):
                product["detail_url"] = self.inject_tag(
                    product["detail_url"], marketplace, user_tag
                )

            # 处理 ASIN 生成的链接
            if product.get("asin") and not product.get("url"):
                asin = product["asin"]
                base_url = self._asin_to_url(asin, marketplace)
                product["url"] = self.inject_tag(base_url, marketplace, user_tag)

        return products

    def generate_affiliate_link(self, asin: str, marketplace: str = "US",
                                 user_tag: str = None) -> str:
        """
        根据 ASIN 生成带 Affiliate Tag 的链接。

        :param asin: Amazon ASIN
        :param marketplace: 站点
        :param user_tag: 用户 Tag
        :return: 完整的 Affiliate 链接
        """
        base_url = self._asin_to_url(asin, marketplace)
        return self.inject_tag(base_url, marketplace, user_tag)

    def process_report_links(self, report_html: str, marketplace: str = "US",
                              user_tag: str = None) -> str:
        """
        处理报告中的所有 Amazon 链接，植入 Affiliate Tag。

        :param report_html: 报告 HTML 内容
        :param marketplace: 站点
        :param user_tag: 用户 Tag
        :return: 处理后的 HTML
        """
        if not report_html:
            return report_html

        # 匹配所有 Amazon 链接
        pattern = r'(https?://(?:www\.)?amazon\.[a-z.]+/[^\s"\'<>]+)'

        def replace_link(match):
            url = match.group(1)
            return self.inject_tag(url, marketplace, user_tag)

        return re.sub(pattern, replace_link, report_html)

    def log_click(self, user_id: int, asin: str, marketplace: str,
                   tag_used: str):
        """记录 Affiliate 点击（用于追踪转化）"""
        try:
            from database.connection import db
            sql = """
                INSERT INTO affiliate_clicks (user_id, asin, marketplace, tag_used, clicked_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            db.execute(sql, (user_id, asin, marketplace, tag_used))
        except Exception as e:
            logger.error(f"[Affiliate] 记录点击失败: {e}")

    # ============================================================
    # 内部方法
    # ============================================================

    def _get_system_tag(self, marketplace: str) -> str:
        """获取系统级 Tag"""
        key = f"amazon_{marketplace.lower()}"
        if marketplace.upper() == "COUPANG":
            key = "coupang"
        return self.system_tags.get(key, "")

    @staticmethod
    def _asin_to_url(asin: str, marketplace: str = "US") -> str:
        """ASIN 转商品链接"""
        domains = {
            "US": "www.amazon.com",
            "UK": "www.amazon.co.uk",
            "DE": "www.amazon.de",
            "JP": "www.amazon.co.jp",
            "CA": "www.amazon.ca",
        }
        domain = domains.get(marketplace.upper(), "www.amazon.com")
        return f"https://{domain}/dp/{asin}"
