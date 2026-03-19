"""
隐性返佣机制 - Affiliate Tag 静默植入

当用户通过系统查看商品详情页或搜索货源时，自动在链接中植入
Affiliate Tag，实现被动收入。

支持平台：
  - Amazon Associates（US / UK / DE / JP / CA 多站点）
  - Coupang Partners（韩国站）
  - 1688/阿里妈妈（中国站 - 淘宝客/1688 分销客）

实现方式：
  - 所有导出的商品链接自动附带 tag
  - 前端跳转链接自动改写
  - 报告中的链接自动植入
  - 1688 搜货结果链接植入阿里妈妈 PID
"""

import re
import os
import hashlib
import time
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
        "default_tag": "",
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

# ============================================================
# Coupang Partners 配置
# ============================================================

COUPANG_AFFILIATE_CONFIG = {
    "domain": "coupang.com",
    "tag_param": "subid",
    "default_tag": "",
}

# ============================================================
# 1688 / 阿里妈妈 返佣配置
# ============================================================

ALIMAMA_AFFILIATE_CONFIG = {
    "1688": {
        "domain": "detail.1688.com",
        "base_url": "https://detail.1688.com/offer/{offer_id}.html",
        "affiliate_base": "https://s.click.1688.com/t",
        "pid_param": "pid",
        "default_pid": "",  # 系统运营方的阿里妈妈 PID
    },
    "taobao": {
        "domain": "item.taobao.com",
        "affiliate_base": "https://s.click.taobao.com/t",
        "pid_param": "pid",
        "default_pid": "",
    },
}

# 第三方服务商返佣配置 (PRD 5.3)
THIRD_PARTY_AFFILIATE_CONFIG = {
    "trademarkia": {
        "name": "Trademarkia",
        "category": "ip_protection",
        "description": "商标查询与注册服务",
        "base_url": "https://www.trademarkia.com",
        "affiliate_param": "ref",
        "default_ref": "",
    },
    "deliverr": {
        "name": "Deliverr",
        "category": "logistics",
        "description": "跨境物流与仓储服务",
        "base_url": "https://www.deliverr.com",
        "affiliate_param": "ref",
        "default_ref": "",
    },
    "helium10": {
        "name": "Helium 10",
        "category": "analytics",
        "description": "Amazon 卖家工具套件",
        "base_url": "https://www.helium10.com",
        "affiliate_param": "ref",
        "default_ref": "",
    },
    "junglescout": {
        "name": "Jungle Scout",
        "category": "analytics",
        "description": "Amazon 选品与市场分析",
        "base_url": "https://www.junglescout.com",
        "affiliate_param": "ref",
        "default_ref": "",
    },
    "canva": {
        "name": "Canva",
        "category": "design",
        "description": "产品图片与 A+ 页面设计",
        "base_url": "https://www.canva.com",
        "affiliate_param": "ref",
        "default_ref": "",
    },
}


class AffiliateManager:
    """
    Affiliate 返佣管理器

    负责：
      1. 在 Amazon/Coupang/1688 链接中植入 Affiliate Tag
      2. 管理系统级和用户级 Tag
      3. 追踪点击和转化
      4. 生成第三方服务商推荐链接
    """

    def __init__(self):
        self.system_tags = {}   # 系统级 Tag（平台运营方收入）
        self.user_tags = {}     # 用户级 Tag
        self._load_system_tags()

    def _load_system_tags(self):
        """从数据库或环境变量加载系统级 Affiliate Tag"""
        # 优先从环境变量加载
        self.system_tags = {
            # Amazon Associates
            "amazon_us": os.getenv("AFFILIATE_TAG_AMAZON_US", ""),
            "amazon_uk": os.getenv("AFFILIATE_TAG_AMAZON_UK", ""),
            "amazon_de": os.getenv("AFFILIATE_TAG_AMAZON_DE", ""),
            "amazon_jp": os.getenv("AFFILIATE_TAG_AMAZON_JP", ""),
            "amazon_ca": os.getenv("AFFILIATE_TAG_AMAZON_CA", ""),
            # Coupang Partners
            "coupang": os.getenv("AFFILIATE_TAG_COUPANG", ""),
            # 阿里妈妈 / 1688 分销客
            "alimama_1688_pid": os.getenv("ALIMAMA_1688_PID", ""),
            "alimama_1688_app_key": os.getenv("ALIMAMA_1688_APP_KEY", ""),
            "alimama_1688_app_secret": os.getenv("ALIMAMA_1688_APP_SECRET", ""),
            "alimama_taobao_pid": os.getenv("ALIMAMA_TAOBAO_PID", ""),
            # 第三方服务商
            "ref_trademarkia": os.getenv("AFFILIATE_REF_TRADEMARKIA", ""),
            "ref_deliverr": os.getenv("AFFILIATE_REF_DELIVERR", ""),
            "ref_helium10": os.getenv("AFFILIATE_REF_HELIUM10", ""),
            "ref_junglescout": os.getenv("AFFILIATE_REF_JUNGLESCOUT", ""),
            "ref_canva": os.getenv("AFFILIATE_REF_CANVA", ""),
        }

        # 尝试从数据库加载（覆盖环境变量）
        try:
            from database.connection import db
            sql = "SELECT config_key, config_value FROM system_config WHERE config_key LIKE 'affiliate_%'"
            rows = db.fetch_all(sql)
            for row in rows:
                key = row["config_key"].replace("affiliate_", "")
                self.system_tags[key] = row["config_value"]
        except Exception:
            pass  # 数据库未初始化时静默跳过

    # ============================================================
    # Amazon / Coupang 链接植入
    # ============================================================

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
        处理报告中的所有 Amazon/1688 链接，植入 Affiliate Tag。

        :param report_html: 报告 HTML 内容
        :param marketplace: 站点
        :param user_tag: 用户 Tag
        :return: 处理后的 HTML
        """
        if not report_html:
            return report_html

        # 匹配 Amazon 链接
        amazon_pattern = r'(https?://(?:www\.)?amazon\.[a-z.]+/[^\s"\'<>]+)'

        def replace_amazon(match):
            url = match.group(1)
            return self.inject_tag(url, marketplace, user_tag)

        result = re.sub(amazon_pattern, replace_amazon, report_html)

        # 匹配 1688 链接
        ali_pattern = r'(https?://(?:detail\.)?1688\.com/[^\s"\'<>]+)'

        def replace_1688(match):
            url = match.group(1)
            return self.inject_1688_tag(url)

        result = re.sub(ali_pattern, replace_1688, result)

        return result

    # ============================================================
    # 1688 / 阿里妈妈 返佣 (PRD 5.2 BIZ-04)
    # ============================================================

    def inject_1688_tag(self, url: str, user_pid: str = None) -> str:
        """
        在 1688 商品链接中植入阿里妈妈 PID 推广位参数。

        阿里妈妈 1688 分销客链接格式:
        https://s.click.1688.com/t?e=...&pid=xxx&unid=...

        :param url: 原始 1688 商品链接
        :param user_pid: 用户自定义 PID（可选）
        :return: 植入 PID 后的链接
        """
        if not url:
            return url

        pid = user_pid or self.system_tags.get("alimama_1688_pid", "")
        if not pid:
            return url

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)

            # 提取 offer_id（1688 商品 ID）
            offer_id = self._extract_1688_offer_id(url)

            # 方式一：直接在原链接上追加 PID 参数
            params["pid"] = [pid]
            params["unid"] = [self._generate_unid()]

            # 重建 URL
            new_query = urlencode(params, doseq=True)
            new_url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))

            logger.debug(f"[Affiliate] 1688 PID 植入: offer_id={offer_id}, pid={pid}")
            return new_url

        except Exception as e:
            logger.error(f"[Affiliate] 1688 PID 植入失败: {e}")
            return url

    def generate_1688_affiliate_link(self, offer_id: str,
                                       user_pid: str = None) -> str:
        """
        根据 1688 商品 ID 生成带阿里妈妈 PID 的推广链接。

        :param offer_id: 1688 商品 ID（offer ID）
        :param user_pid: 用户自定义 PID
        :return: 完整的 1688 推广链接
        """
        pid = user_pid or self.system_tags.get("alimama_1688_pid", "")
        base_url = f"https://detail.1688.com/offer/{offer_id}.html"

        if not pid:
            return base_url

        # 构建阿里妈妈推广链接
        params = {
            "pid": pid,
            "unid": self._generate_unid(),
            "e": self._generate_alimama_e_param(offer_id, pid),
        }

        affiliate_url = f"{ALIMAMA_AFFILIATE_CONFIG['1688']['affiliate_base']}?{urlencode(params)}"
        return affiliate_url

    def inject_1688_tags_batch(self, suppliers: list[dict],
                                 user_pid: str = None) -> list[dict]:
        """
        批量为 1688 供应商列表中的链接植入阿里妈妈 PID。

        :param suppliers: 供应商列表（来自 1688 以图搜货结果）
        :param user_pid: 用户自定义 PID
        :return: 处理后的供应商列表
        """
        for supplier in suppliers:
            # 处理商品链接
            if supplier.get("product_url"):
                supplier["product_url"] = self.inject_1688_tag(
                    supplier["product_url"], user_pid
                )

            # 处理店铺链接
            if supplier.get("shop_url"):
                supplier["shop_url"] = self.inject_1688_tag(
                    supplier["shop_url"], user_pid
                )

            # 如果有 offer_id 但没有链接，生成推广链接
            if supplier.get("offer_id") and not supplier.get("product_url"):
                supplier["product_url"] = self.generate_1688_affiliate_link(
                    supplier["offer_id"], user_pid
                )

        return suppliers

    def log_1688_click(self, user_id: int, offer_id: str, pid_used: str,
                        supplier_name: str = ""):
        """记录 1688 推广点击"""
        try:
            from database.connection import db
            sql = """
                INSERT INTO affiliate_clicks
                    (user_id, asin, marketplace, tag_used, clicked_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            # 复用 affiliate_clicks 表，asin 字段存 offer_id，marketplace 存 '1688'
            db.execute(sql, (user_id, offer_id, "1688", pid_used))
            logger.info(f"[Affiliate] 1688 点击记录: user={user_id}, offer={offer_id}")
        except Exception as e:
            logger.error(f"[Affiliate] 1688 点击记录失败: {e}")

    # ============================================================
    # 第三方服务商推荐链接 (PRD 5.3 BIZ-05)
    # ============================================================

    def generate_service_link(self, service_id: str, path: str = "",
                                user_ref: str = None) -> str:
        """
        生成第三方服务商推荐链接（含返佣参数）。

        :param service_id: 服务商 ID（trademarkia/deliverr/helium10 等）
        :param path: 链接路径（可选）
        :param user_ref: 用户自定义 ref code
        :return: 带返佣参数的链接
        """
        config = THIRD_PARTY_AFFILIATE_CONFIG.get(service_id)
        if not config:
            return ""

        ref = user_ref or self.system_tags.get(f"ref_{service_id}", "")
        base = config["base_url"]
        url = f"{base}{path}" if path else base

        if not ref:
            return url

        # 植入 ref 参数
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params[config["affiliate_param"]] = [ref]
        new_query = urlencode(params, doseq=True)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))

    def get_recommended_services(self, risk_dimensions: dict = None) -> list[dict]:
        """
        根据风险分析结果推荐相关第三方服务商。

        :param risk_dimensions: 风险维度分数 {competition, demand, profit, ip_risk, seasonality}
        :return: 推荐服务商列表
        """
        recommendations = []

        for service_id, config in THIRD_PARTY_AFFILIATE_CONFIG.items():
            rec = {
                "service_id": service_id,
                "name": config["name"],
                "category": config["category"],
                "description": config["description"],
                "url": self.generate_service_link(service_id),
                "relevance": "medium",
            }

            # 根据风险维度调整推荐优先级
            if risk_dimensions:
                if service_id == "trademarkia" and risk_dimensions.get("ip_risk", 0) >= 40:
                    rec["relevance"] = "high"
                    rec["reason"] = "检测到知识产权风险较高，建议进行商标查询"
                elif service_id == "deliverr" and risk_dimensions.get("seasonality", 0) >= 50:
                    rec["relevance"] = "high"
                    rec["reason"] = "产品有季节性波动，建议使用弹性仓储物流"
                elif service_id in ("helium10", "junglescout") and risk_dimensions.get("competition", 0) >= 50:
                    rec["relevance"] = "high"
                    rec["reason"] = "市场竞争激烈，建议使用专业分析工具深入研究"
                elif service_id == "canva":
                    rec["relevance"] = "medium"
                    rec["reason"] = "提升 Listing 视觉效果，增强竞争力"

            recommendations.append(rec)

        # 按相关性排序：high > medium > low
        relevance_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: relevance_order.get(x["relevance"], 1))

        return recommendations

    def log_service_click(self, user_id: int, service_id: str):
        """记录第三方服务商推荐点击"""
        try:
            from database.connection import db
            sql = """
                INSERT INTO affiliate_clicks
                    (user_id, asin, marketplace, tag_used, clicked_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            db.execute(sql, (user_id, service_id, "third_party", service_id))
        except Exception as e:
            logger.error(f"[Affiliate] 服务商点击记录失败: {e}")

    # ============================================================
    # 通用点击追踪
    # ============================================================

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

    @staticmethod
    def _extract_1688_offer_id(url: str) -> str:
        """从 1688 链接中提取 offer ID"""
        # 匹配 /offer/12345.html 格式
        match = re.search(r'/offer/(\d+)\.html', url)
        if match:
            return match.group(1)

        # 匹配 offerId=12345 参数格式
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "offerId" in params:
            return params["offerId"][0]

        return ""

    @staticmethod
    def _generate_unid() -> str:
        """生成唯一追踪 ID"""
        timestamp = str(int(time.time() * 1000))
        random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"{timestamp}_{random_part}"

    @staticmethod
    def _generate_alimama_e_param(offer_id: str, pid: str) -> str:
        """
        生成阿里妈妈 e 参数（加密的推广信息）。
        实际生产环境中需要使用阿里妈妈 API 生成，
        这里提供基础的签名实现。
        """
        raw = f"{offer_id}|{pid}|{int(time.time())}"
        signature = hashlib.md5(raw.encode()).hexdigest()
        return signature
