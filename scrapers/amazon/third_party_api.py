"""
第三方数据源 API 集成

针对亚马逊未开放的深度数据（如历史价格、精准销量预估），
集成第三方工具的 API：
  - Keepa API: 历史价格追踪、BSR 历史、销量预估
  - Rainforest API: 实时产品数据、评论数据、搜索结果
"""

import time
from typing import Optional

import requests

from utils.logger import get_logger

logger = get_logger()


class KeepaClient:
    """
    Keepa API 客户端

    提供亚马逊产品的历史数据：
      - 价格历史曲线
      - BSR 排名历史
      - 评论数增长趋势
      - 销量预估
      - 新品/变体追踪

    API 文档: https://keepa.com/#!discuss/t/using-the-keepa-api/47
    """

    BASE_URL = "https://api.keepa.com"

    # Keepa 域名 ID 映射
    DOMAIN_IDS = {
        "US": 1, "UK": 2, "DE": 3, "FR": 4, "JP": 5,
        "CA": 6, "IT": 8, "ES": 9, "MX": 11, "AU": 13,
    }

    def __init__(self, api_key: str, marketplace: str = "US"):
        """
        :param api_key: Keepa API Key
        :param marketplace: 目标站点
        """
        self.api_key = api_key
        self.marketplace = marketplace.upper()
        self.domain_id = self.DOMAIN_IDS.get(self.marketplace, 1)

    def get_product(self, asins: list[str], stats: int = 30,
                    history: bool = True, offers: int = 0) -> list[dict]:
        """
        获取产品详细数据（含历史）。

        :param asins: ASIN 列表（每次最多 100 个）
        :param stats: 统计天数（如 30 表示近30天）
        :param history: 是否包含价格历史
        :param offers: 获取 offer 数量（0 表示不获取）
        :return: 产品数据列表
        """
        params = {
            "key": self.api_key,
            "domain": self.domain_id,
            "asin": ",".join(asins[:100]),
            "stats": stats,
            "history": 1 if history else 0,
            "offers": offers,
        }

        try:
            resp = requests.get(f"{self.BASE_URL}/product", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            products = data.get("products", [])
            return [self._parse_keepa_product(p) for p in products]

        except Exception as e:
            logger.error(f"[Keepa] 获取产品数据失败: {e}")
            return []

    def _parse_keepa_product(self, product: dict) -> dict:
        """解析 Keepa 产品数据"""
        stats = product.get("stats", {})
        parsed = product.get("stats_parsed", {})

        result = {
            "asin": product.get("asin", ""),
            "title": product.get("title", ""),
            "brand": product.get("brand", ""),
            "product_group": product.get("productGroup", ""),
            "category_tree": product.get("categoryTree", []),

            # 当前数据
            "current_price": self._keepa_price(stats.get("current", [None])[0]),
            "current_bsr": stats.get("current", [None, None, None])[2] if len(stats.get("current", [])) > 2 else None,

            # 统计数据（近 N 天）
            "avg_price": self._keepa_price(stats.get("avg", [None])[0]),
            "min_price": self._keepa_price(stats.get("min", [None])[0]),
            "max_price": self._keepa_price(stats.get("max", [None])[0]),
            "avg_bsr": stats.get("avg", [None, None, None])[2] if len(stats.get("avg", [])) > 2 else None,

            # 销量预估
            "estimated_monthly_sales": stats.get("monthlySold", 0),
            "estimated_monthly_revenue": stats.get("monthlyRevenue", 0),

            # 评论数据
            "review_count": product.get("csv", [[]])[16][-1] if product.get("csv") and len(product.get("csv", [])) > 16 else 0,
            "rating": product.get("csv", [[]])[17][-1] / 10 if product.get("csv") and len(product.get("csv", [])) > 17 else 0,

            # 卖家数量
            "offer_count_new": stats.get("offerCountNew", 0),
            "offer_count_used": stats.get("offerCountUsed", 0),

            # 上架时间
            "listed_since": product.get("listedSince", 0),

            # FBA 相关
            "is_fba": product.get("isFBA", False),
            "fba_fees": product.get("fbaFees", {}),

            # 变体数量
            "variation_count": len(product.get("variations", [])),
        }

        return result

    def get_best_sellers(self, category_id: int) -> list[dict]:
        """获取类目 Best Sellers 列表"""
        params = {
            "key": self.api_key,
            "domain": self.domain_id,
            "category": category_id,
        }

        try:
            resp = requests.get(f"{self.BASE_URL}/bestsellers", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("bestSellersList", {}).get("asinList", [])
        except Exception as e:
            logger.error(f"[Keepa] 获取 Best Sellers 失败: {e}")
            return []

    def search_products(self, keyword: str, sort: int = 0,
                        per_page: int = 50) -> list[str]:
        """
        通过关键词搜索产品（返回 ASIN 列表）。

        :param keyword: 搜索关键词
        :param sort: 排序方式 (0=相关性, 1=价格升序, 2=价格降序, 3=评论数)
        :param per_page: 每页数量
        :return: ASIN 列表
        """
        params = {
            "key": self.api_key,
            "domain": self.domain_id,
            "type": "product",
            "term": keyword,
            "sort": sort,
            "perPage": per_page,
        }

        try:
            resp = requests.get(f"{self.BASE_URL}/search", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("asinList", [])
        except Exception as e:
            logger.error(f"[Keepa] 搜索产品失败: {e}")
            return []

    def get_tokens_left(self) -> int:
        """查询剩余 API Token 数量"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/token",
                params={"key": self.api_key},
                timeout=10
            )
            data = resp.json()
            return data.get("tokensLeft", 0)
        except Exception:
            return -1

    @staticmethod
    def _keepa_price(value) -> Optional[float]:
        """将 Keepa 价格（分）转换为美元"""
        if value is None or value < 0:
            return None
        return value / 100.0


class RainforestClient:
    """
    Rainforest API 客户端

    提供亚马逊实时数据抓取服务：
      - 搜索结果
      - 产品详情
      - 评论数据
      - 类目数据
      - 卖家信息

    API 文档: https://www.rainforestapi.com/docs
    """

    BASE_URL = "https://api.rainforestapi.com/request"

    # Rainforest 站点域名映射
    AMAZON_DOMAINS = {
        "US": "amazon.com", "UK": "amazon.co.uk", "DE": "amazon.de",
        "FR": "amazon.fr", "JP": "amazon.co.jp", "CA": "amazon.ca",
        "IT": "amazon.it", "ES": "amazon.es", "AU": "amazon.com.au",
        "MX": "amazon.com.mx",
    }

    def __init__(self, api_key: str, marketplace: str = "US"):
        self.api_key = api_key
        self.marketplace = marketplace.upper()
        self.amazon_domain = self.AMAZON_DOMAINS.get(self.marketplace, "amazon.com")

    def search(self, keyword: str, page: int = 1,
               sort_by: str = "relevance") -> dict:
        """
        搜索亚马逊产品。

        :return: {search_results: [...], total_results: int}
        """
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": self.amazon_domain,
            "search_term": keyword,
            "page": page,
            "sort_by": sort_by,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("search_results", [])
            parsed = []
            for item in results:
                parsed.append({
                    "asin": item.get("asin", ""),
                    "title": item.get("title", ""),
                    "price": item.get("price", {}).get("value"),
                    "currency": item.get("price", {}).get("currency", "USD"),
                    "rating": item.get("rating", 0),
                    "review_count": item.get("ratings_total", 0),
                    "main_image": item.get("image", ""),
                    "is_prime": item.get("is_prime", False),
                    "is_sponsored": item.get("is_sponsored", False),
                    "position": item.get("position", 0),
                    "bsr": item.get("bestsellers_rank", 0),
                    "source": "rainforest-api",
                })

            return {
                "search_results": parsed,
                "total_results": data.get("search_information", {}).get("total_results", 0),
            }

        except Exception as e:
            logger.error(f"[Rainforest] 搜索失败: {e}")
            return {"search_results": [], "total_results": 0}

    def get_product(self, asin: str) -> Optional[dict]:
        """获取产品详情"""
        params = {
            "api_key": self.api_key,
            "type": "product",
            "amazon_domain": self.amazon_domain,
            "asin": asin,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            product = data.get("product", {})

            return {
                "asin": product.get("asin", ""),
                "title": product.get("title", ""),
                "brand": product.get("brand", ""),
                "price": product.get("buybox_winner", {}).get("price", {}).get("value"),
                "rating": product.get("rating", 0),
                "review_count": product.get("ratings_total", 0),
                "main_image": product.get("main_image", {}).get("link", ""),
                "images": [img.get("link", "") for img in product.get("images", [])],
                "bsr_ranks": [
                    {"rank": r.get("rank", 0), "category": r.get("category", "")}
                    for r in product.get("bestsellers_rank", [])
                ],
                "fulfillment_type": "FBA" if product.get("fulfillment", {}).get("is_fulfilled_by_amazon") else "FBM",
                "categories": [c.get("name", "") for c in product.get("categories", [])],
                "attributes": product.get("attributes", []),
                "feature_bullets": product.get("feature_bullets", []),
                "description": product.get("description", ""),
                "variants": product.get("variants", []),
                "source": "rainforest-api",
            }

        except Exception as e:
            logger.error(f"[Rainforest] 获取产品详情失败: {e}")
            return None

    def get_reviews(self, asin: str, page: int = 1,
                    sort_by: str = "most_recent",
                    star_rating: str = None) -> dict:
        """获取产品评论"""
        params = {
            "api_key": self.api_key,
            "type": "reviews",
            "amazon_domain": self.amazon_domain,
            "asin": asin,
            "page": page,
            "sort_by": sort_by,
        }
        if star_rating:
            params["star_rating"] = star_rating

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            reviews = []
            for r in data.get("reviews", []):
                reviews.append({
                    "review_id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "rating": r.get("rating", 0),
                    "date": r.get("date", {}).get("raw", ""),
                    "author": r.get("profile", {}).get("name", ""),
                    "verified_purchase": r.get("verified_purchase", False),
                    "helpful_votes": r.get("helpful_votes", 0),
                    "images": [img.get("link", "") for img in r.get("images", [])],
                })

            return {
                "reviews": reviews,
                "total_reviews": data.get("summary", {}).get("ratings_total", 0),
                "average_rating": data.get("summary", {}).get("rating", 0),
            }

        except Exception as e:
            logger.error(f"[Rainforest] 获取评论失败: {e}")
            return {"reviews": [], "total_reviews": 0, "average_rating": 0}

    def test_connection(self) -> bool:
        """测试 API 连接是否有效"""
        try:
            params = {
                "api_key": self.api_key,
                "type": "search",
                "amazon_domain": "amazon.com",
                "search_term": "test",
                "page": 1,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            return resp.status_code == 200
        except Exception:
            return False
