"""
Keepa API 客户端 - 独立封装

完整实现 PRD 11.2 定义的 Keepa API 集成：
  - Product Request: 产品数据 + 历史价格/BSR/评论趋势
  - Best Sellers: 类目畅销榜
  - Product Search: 关键词搜索
  - Token 余量查询
  - BSR 历史时间序列解析
  - Buy Box 价格追踪

API 文档: https://keepa.com/#!discuss/t/using-the-keepa-api/47
"""

import time
from datetime import datetime, timedelta
from typing import Optional

import requests

from utils.logger import get_logger

logger = get_logger()


class KeepaClient:
    """
    Keepa API 客户端

    PRD 11.2 参考：
      - domain: 站点编号 (1=US, 2=UK, 3=DE, ...)
      - asin: 支持逗号分隔批量查询，最多 100 个
      - stats: 统计周期天数
      - history: 是否返回完整历史数据
      - offers: 是否返回 Offer 列表

    csv 数组索引：
      - 0: Amazon Price
      - 1: New Price (3rd party)
      - 2: Used Price
      - 3: Sales Rank
      - 11: New Offer Count
      - 16: Rating
      - 17: Review Count
      - 18: Buy Box Price
    """

    BASE_URL = "https://api.keepa.com"

    # Keepa 域名 ID 映射 (PRD 11.2)
    DOMAIN_IDS = {
        "US": 1, "UK": 2, "DE": 3, "FR": 4, "JP": 5,
        "CA": 6, "CN": 7, "IT": 8, "ES": 9, "IN": 10,
        "MX": 11, "BR": 12, "AU": 13,
    }

    # csv 数组索引常量
    CSV_AMAZON_PRICE = 0
    CSV_NEW_PRICE = 1
    CSV_USED_PRICE = 2
    CSV_SALES_RANK = 3
    CSV_LIST_PRICE = 4
    CSV_COLLECTIBLE_PRICE = 5
    CSV_REFURBISHED_PRICE = 6
    CSV_NEW_FBM_SHIPPING = 7
    CSV_LIGHTNING_DEAL = 8
    CSV_WAREHOUSE_DEAL = 9
    CSV_NEW_FBA_PRICE = 10
    CSV_NEW_OFFER_COUNT = 11
    CSV_USED_OFFER_COUNT = 12
    CSV_RATING = 16
    CSV_REVIEW_COUNT = 17
    CSV_BUY_BOX_PRICE = 18

    # Keepa 时间基准 (2011-01-01 00:00:00 UTC, 以分钟为单位)
    KEEPA_EPOCH_MINUTES = 21564000  # minutes from Unix epoch to 2011-01-01

    def __init__(self, api_key: str, marketplace: str = "US"):
        """
        :param api_key: Keepa API Key
        :param marketplace: 目标站点代码 (US/UK/DE/FR/JP/CA/IT/ES/MX/AU)
        """
        self.api_key = api_key
        self.marketplace = marketplace.upper()
        self.domain_id = self.DOMAIN_IDS.get(self.marketplace, 1)
        self._tokens_left = None
        self._rate_limit_until = 0

    # ──────────────────────────────────────────────
    # 核心 API: Product Request
    # ──────────────────────────────────────────────

    def get_product(self, asins: list[str], stats: int = 30,
                    history: bool = True, offers: int = 0,
                    rating: bool = True, buybox: bool = True) -> list[dict]:
        """
        获取产品详细数据（含历史）。

        :param asins: ASIN 列表（每次最多 100 个）
        :param stats: 统计天数（如 30 表示近30天）
        :param history: 是否包含价格历史
        :param offers: 获取 offer 数量（0 表示不获取）
        :param rating: 是否包含评分历史
        :param buybox: 是否包含 Buy Box 历史
        :return: 解析后的产品数据列表
        """
        self._wait_rate_limit()

        params = {
            "key": self.api_key,
            "domain": self.domain_id,
            "asin": ",".join(asins[:100]),
            "stats": stats,
            "history": 1 if history else 0,
            "offers": offers,
            "rating": 1 if rating else 0,
            "buybox": 1 if buybox else 0,
        }

        try:
            resp = requests.get(f"{self.BASE_URL}/product", params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            self._update_tokens(data)
            products = data.get("products", [])
            return [self._parse_product(p, include_history=history) for p in products]

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                logger.warning("[Keepa] Rate limited, backing off 60s")
                self._rate_limit_until = time.time() + 60
            logger.error(f"[Keepa] 获取产品数据失败: {e}")
            return []
        except Exception as e:
            logger.error(f"[Keepa] 获取产品数据失败: {e}")
            return []

    def get_product_batch(self, asins: list[str], stats: int = 30,
                          batch_size: int = 100, **kwargs) -> list[dict]:
        """
        批量获取产品数据，自动分批处理。

        :param asins: 完整 ASIN 列表（不限数量）
        :param batch_size: 每批数量（最大 100）
        :return: 所有产品数据
        """
        all_results = []
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            results = self.get_product(batch, stats=stats, **kwargs)
            all_results.extend(results)

            # 批次间等待，避免触发限流
            if i + batch_size < len(asins):
                time.sleep(2)

        return all_results

    # ──────────────────────────────────────────────
    # Best Sellers
    # ──────────────────────────────────────────────

    def get_best_sellers(self, category_id: int) -> list[str]:
        """
        获取类目 Best Sellers 列表。

        :param category_id: Amazon 类目节点 ID
        :return: ASIN 列表
        """
        self._wait_rate_limit()

        params = {
            "key": self.api_key,
            "domain": self.domain_id,
            "category": category_id,
        }

        try:
            resp = requests.get(f"{self.BASE_URL}/bestsellers", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self._update_tokens(data)
            return data.get("bestSellersList", {}).get("asinList", [])
        except Exception as e:
            logger.error(f"[Keepa] 获取 Best Sellers 失败: {e}")
            return []

    # ──────────────────────────────────────────────
    # Product Search
    # ──────────────────────────────────────────────

    def search_products(self, keyword: str, sort: int = 0,
                        per_page: int = 50) -> list[str]:
        """
        通过关键词搜索产品（返回 ASIN 列表）。

        :param keyword: 搜索关键词
        :param sort: 排序方式 (0=相关性, 1=价格升序, 2=价格降序, 3=评论数)
        :param per_page: 每页数量
        :return: ASIN 列表
        """
        self._wait_rate_limit()

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
            self._update_tokens(data)
            return data.get("asinList", [])
        except Exception as e:
            logger.error(f"[Keepa] 搜索产品失败: {e}")
            return []

    # ──────────────────────────────────────────────
    # Token 管理
    # ──────────────────────────────────────────────

    def get_tokens_left(self) -> int:
        """查询剩余 API Token 数量"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/token",
                params={"key": self.api_key},
                timeout=10
            )
            data = resp.json()
            self._tokens_left = data.get("tokensLeft", 0)
            return self._tokens_left
        except Exception:
            return -1

    @property
    def tokens_left(self) -> Optional[int]:
        """最近一次 API 调用后的剩余 token 数"""
        return self._tokens_left

    # ──────────────────────────────────────────────
    # 数据解析
    # ──────────────────────────────────────────────

    def _parse_product(self, product: dict, include_history: bool = True) -> dict:
        """
        解析 Keepa 产品数据为标准化格式。

        按 PRD 11.2 的 csv 数组索引解析：
          - 索引 0: Amazon Price
          - 索引 1: New Price
          - 索引 16: Rating
          - 索引 17: Review Count
          - 索引 18: Buy Box Price
        """
        stats = product.get("stats", {})
        csv_data = product.get("csv", [])

        result = {
            "asin": product.get("asin", ""),
            "title": product.get("title", ""),
            "brand": product.get("brand", ""),
            "product_group": product.get("productGroup", ""),
            "category_tree": product.get("categoryTree", []),
            "parent_asin": product.get("parentAsin", ""),
            "variation_count": len(product.get("variations", [])),

            # 当前数据
            "current_amazon_price": self._extract_csv_current(csv_data, self.CSV_AMAZON_PRICE),
            "current_new_price": self._extract_csv_current(csv_data, self.CSV_NEW_PRICE),
            "current_buybox_price": self._extract_csv_current(csv_data, self.CSV_BUY_BOX_PRICE),
            "current_bsr": self._extract_csv_current(csv_data, self.CSV_SALES_RANK, is_price=False),
            "current_rating": self._extract_csv_current(csv_data, self.CSV_RATING, is_price=False, divisor=10),
            "current_review_count": self._extract_csv_current(csv_data, self.CSV_REVIEW_COUNT, is_price=False),

            # 统计数据（近 N 天）
            "stats_period_days": stats.get("outOfStockPercentageInInterval", 0),
            "avg_price": self._keepa_price(self._safe_stat(stats, "avg", 0)),
            "min_price": self._keepa_price(self._safe_stat(stats, "min", 0)),
            "max_price": self._keepa_price(self._safe_stat(stats, "max", 0)),
            "avg_bsr": self._safe_stat(stats, "avg", 3),

            # 销量预估
            "estimated_monthly_sales": stats.get("monthlySold", 0),
            "estimated_monthly_revenue": stats.get("monthlyRevenue", 0),
            "sales_rank_drops_30": stats.get("salesRankDrops30", 0),
            "sales_rank_drops_90": stats.get("salesRankDrops90", 0),
            "sales_rank_drops_180": stats.get("salesRankDrops180", 0),

            # Offer 数据
            "offer_count_new": stats.get("offerCountNew", 0),
            "offer_count_used": stats.get("offerCountUsed", 0),
            "buy_box_seller": product.get("buyBoxSellerId", ""),
            "buy_box_is_amazon": product.get("buyBoxIsAmazon", False),

            # 上架信息
            "listed_since": self._keepa_time_to_datetime(product.get("listedSince", 0)),
            "is_fba": product.get("isFBA", False),
            "fba_fees": product.get("fbaFees", {}),

            # 缺货率
            "out_of_stock_percentage_30": stats.get("outOfStockPercentage30", [0])[0] if isinstance(stats.get("outOfStockPercentage30"), list) else stats.get("outOfStockPercentage30", 0),

            # 数据来源
            "source": "keepa",
        }

        # 添加历史时间序列数据
        if include_history and csv_data:
            result["price_history"] = self._parse_time_series(csv_data, self.CSV_AMAZON_PRICE)
            result["new_price_history"] = self._parse_time_series(csv_data, self.CSV_NEW_PRICE)
            result["bsr_history"] = self._parse_time_series(csv_data, self.CSV_SALES_RANK, is_price=False)
            result["buybox_history"] = self._parse_time_series(csv_data, self.CSV_BUY_BOX_PRICE)
            result["review_count_history"] = self._parse_time_series(csv_data, self.CSV_REVIEW_COUNT, is_price=False)
            result["rating_history"] = self._parse_time_series(csv_data, self.CSV_RATING, is_price=False, divisor=10)
            result["new_offer_count_history"] = self._parse_time_series(csv_data, self.CSV_NEW_OFFER_COUNT, is_price=False)

        return result

    def _parse_time_series(self, csv_data: list, index: int,
                           is_price: bool = True, divisor: float = 1,
                           days_back: int = 365) -> list[dict]:
        """
        解析 Keepa csv 数组中的时间序列数据。

        Keepa csv 格式: [keepa_minutes_1, value_1, keepa_minutes_2, value_2, ...]
        Keepa 时间: 从 2011-01-01 00:00 UTC 起的分钟数

        :param csv_data: 完整 csv 数组
        :param index: csv 数组索引
        :param is_price: 是否为价格数据（需要除以 100）
        :param divisor: 额外除数（如 rating 需要 /10）
        :param days_back: 只返回最近 N 天的数据
        :return: [{"date": "2025-01-01", "value": 29.99}, ...]
        """
        if not csv_data or index >= len(csv_data) or not csv_data[index]:
            return []

        series = csv_data[index]
        if not isinstance(series, list) or len(series) < 2:
            return []

        cutoff = datetime.utcnow() - timedelta(days=days_back)
        result = []

        for i in range(0, len(series) - 1, 2):
            keepa_minutes = series[i]
            raw_value = series[i + 1]

            if raw_value is None or raw_value < 0:
                continue

            dt = self._keepa_minutes_to_datetime(keepa_minutes)
            if dt and dt >= cutoff:
                value = raw_value
                if is_price:
                    value = value / 100.0
                if divisor != 1:
                    value = value / divisor

                result.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "timestamp": int(dt.timestamp()),
                    "value": round(value, 2),
                })

        return result

    def _extract_csv_current(self, csv_data: list, index: int,
                             is_price: bool = True, divisor: float = 1) -> Optional[float]:
        """提取 csv 数组中某个指标的最新值"""
        if not csv_data or index >= len(csv_data) or not csv_data[index]:
            return None

        series = csv_data[index]
        if not isinstance(series, list) or len(series) < 2:
            return None

        raw_value = series[-1]
        if raw_value is None or raw_value < 0:
            return None

        value = raw_value
        if is_price:
            value = value / 100.0
        if divisor != 1:
            value = value / divisor

        return round(value, 2)

    # ──────────────────────────────────────────────
    # 高级分析方法
    # ──────────────────────────────────────────────

    def analyze_price_stability(self, asin: str, days: int = 90) -> dict:
        """
        分析产品价格稳定性。

        :return: {
            "avg_price": float,
            "price_volatility": float (标准差/均值),
            "price_drops_count": int,
            "max_drop_pct": float,
            "is_stable": bool
        }
        """
        products = self.get_product([asin], stats=days)
        if not products:
            return {"error": "Product not found"}

        product = products[0]
        history = product.get("price_history", [])

        if len(history) < 3:
            return {
                "avg_price": product.get("avg_price"),
                "price_volatility": 0,
                "price_drops_count": 0,
                "max_drop_pct": 0,
                "is_stable": True,
                "data_points": len(history),
            }

        prices = [p["value"] for p in history if p["value"] > 0]
        if not prices:
            return {"error": "No valid price data"}

        import statistics
        avg = statistics.mean(prices)
        std = statistics.stdev(prices) if len(prices) > 1 else 0
        volatility = std / avg if avg > 0 else 0

        # 计算价格下跌次数和最大跌幅
        drops = 0
        max_drop_pct = 0
        for i in range(1, len(prices)):
            if prices[i] < prices[i - 1]:
                drops += 1
                drop_pct = (prices[i - 1] - prices[i]) / prices[i - 1]
                max_drop_pct = max(max_drop_pct, drop_pct)

        return {
            "avg_price": round(avg, 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "price_volatility": round(volatility, 4),
            "price_drops_count": drops,
            "max_drop_pct": round(max_drop_pct, 4),
            "is_stable": volatility < 0.15,
            "data_points": len(prices),
        }

    def analyze_bsr_trend(self, asin: str, days: int = 90) -> dict:
        """
        分析 BSR 排名趋势。

        :return: {
            "current_bsr": int,
            "avg_bsr": float,
            "bsr_trend": "improving" | "declining" | "stable",
            "bsr_volatility": float,
            "sales_velocity": str
        }
        """
        products = self.get_product([asin], stats=days)
        if not products:
            return {"error": "Product not found"}

        product = products[0]
        bsr_history = product.get("bsr_history", [])

        current_bsr = product.get("current_bsr")
        avg_bsr = product.get("avg_bsr")

        if not bsr_history or len(bsr_history) < 3:
            return {
                "current_bsr": current_bsr,
                "avg_bsr": avg_bsr,
                "bsr_trend": "unknown",
                "data_points": len(bsr_history),
            }

        bsr_values = [p["value"] for p in bsr_history if p["value"] > 0]
        if not bsr_values:
            return {"error": "No valid BSR data"}

        import statistics
        avg = statistics.mean(bsr_values)
        std = statistics.stdev(bsr_values) if len(bsr_values) > 1 else 0

        # BSR 趋势判断（取前半段和后半段的均值比较）
        mid = len(bsr_values) // 2
        first_half_avg = statistics.mean(bsr_values[:mid]) if mid > 0 else avg
        second_half_avg = statistics.mean(bsr_values[mid:]) if mid > 0 else avg

        if second_half_avg < first_half_avg * 0.85:
            trend = "improving"  # BSR 下降 = 排名提升
        elif second_half_avg > first_half_avg * 1.15:
            trend = "declining"  # BSR 上升 = 排名下降
        else:
            trend = "stable"

        # 销售速度评估
        drops_30 = product.get("sales_rank_drops_30", 0)
        if drops_30 > 300:
            velocity = "very_high"
        elif drops_30 > 100:
            velocity = "high"
        elif drops_30 > 30:
            velocity = "medium"
        else:
            velocity = "low"

        return {
            "current_bsr": current_bsr,
            "avg_bsr": round(avg, 0),
            "best_bsr": min(bsr_values),
            "worst_bsr": max(bsr_values),
            "bsr_trend": trend,
            "bsr_volatility": round(std / avg, 4) if avg > 0 else 0,
            "sales_rank_drops_30": drops_30,
            "sales_rank_drops_90": product.get("sales_rank_drops_90", 0),
            "sales_velocity": velocity,
            "estimated_monthly_sales": product.get("estimated_monthly_sales", 0),
            "data_points": len(bsr_values),
        }

    def analyze_review_growth(self, asin: str, days: int = 180) -> dict:
        """
        分析评论增长趋势，用于推算产品生命周期。

        :return: {
            "current_reviews": int,
            "review_growth_rate": float (每月增长数),
            "estimated_launch_date": str,
            "lifecycle_stage": str
        }
        """
        products = self.get_product([asin], stats=days)
        if not products:
            return {"error": "Product not found"}

        product = products[0]
        review_history = product.get("review_count_history", [])
        current_reviews = product.get("current_review_count", 0)

        if not review_history or len(review_history) < 2:
            return {
                "current_reviews": current_reviews,
                "review_growth_rate": 0,
                "lifecycle_stage": "unknown",
            }

        # 计算月均评论增长
        first = review_history[0]
        last = review_history[-1]
        days_span = max((last["timestamp"] - first["timestamp"]) / 86400, 1)
        review_growth = last["value"] - first["value"]
        monthly_growth = review_growth / (days_span / 30)

        # 推算上架时间
        listed_since = product.get("listed_since")

        # 生命周期阶段判断
        if monthly_growth > 100:
            stage = "rapid_growth"
        elif monthly_growth > 30:
            stage = "growth"
        elif monthly_growth > 10:
            stage = "mature"
        elif monthly_growth > 0:
            stage = "declining"
        else:
            stage = "stagnant"

        return {
            "current_reviews": current_reviews,
            "current_rating": product.get("current_rating"),
            "review_growth_total": review_growth,
            "review_growth_monthly": round(monthly_growth, 1),
            "analysis_days": round(days_span),
            "estimated_launch_date": listed_since,
            "lifecycle_stage": stage,
        }

    # ──────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────

    @staticmethod
    def _keepa_price(value) -> Optional[float]:
        """将 Keepa 价格（分）转换为美元"""
        if value is None or value < 0:
            return None
        return round(value / 100.0, 2)

    @staticmethod
    def _safe_stat(stats: dict, key: str, index: int):
        """安全获取 stats 中的嵌套值"""
        arr = stats.get(key, [])
        if isinstance(arr, list) and len(arr) > index:
            return arr[index]
        return None

    @staticmethod
    def _keepa_minutes_to_datetime(keepa_minutes: int) -> Optional[datetime]:
        """将 Keepa 分钟时间戳转换为 datetime"""
        if not keepa_minutes or keepa_minutes <= 0:
            return None
        # Keepa epoch: 2011-01-01 00:00:00 UTC
        keepa_epoch = datetime(2011, 1, 1)
        return keepa_epoch + timedelta(minutes=keepa_minutes)

    def _keepa_time_to_datetime(self, keepa_minutes: int) -> Optional[str]:
        """将 Keepa 分钟时间戳转换为 ISO 日期字符串"""
        dt = self._keepa_minutes_to_datetime(keepa_minutes)
        return dt.strftime("%Y-%m-%d") if dt else None

    def _update_tokens(self, response_data: dict):
        """更新 token 余量"""
        self._tokens_left = response_data.get("tokensLeft", self._tokens_left)

    def _wait_rate_limit(self):
        """等待限流解除"""
        now = time.time()
        if now < self._rate_limit_until:
            wait_time = self._rate_limit_until - now
            logger.info(f"[Keepa] Rate limit active, waiting {wait_time:.0f}s")
            time.sleep(wait_time)

    def test_connection(self) -> dict:
        """
        测试 API 连接是否有效。

        :return: {"connected": bool, "tokens_left": int}
        """
        tokens = self.get_tokens_left()
        return {
            "connected": tokens >= 0,
            "tokens_left": tokens,
            "marketplace": self.marketplace,
            "domain_id": self.domain_id,
        }
