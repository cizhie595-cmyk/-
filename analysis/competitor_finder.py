"""
竞品发现引擎 - Step 4 增强模块
自动发现同类竞品，分析竞争格局，生成竞品对比矩阵。
"""

import re
from datetime import datetime
from typing import Optional
from loguru import logger


class CompetitorFinder:
    """
    竞品发现引擎
    - 基于关键词搜索发现竞品
    - 基于 BSR 类目排名发现竞品
    - 基于 "Frequently Bought Together" 发现竞品
    - 竞品对比矩阵生成
    - 竞争格局分析（市场集中度、价格带分布）
    """

    def __init__(self, db=None, http_client=None, marketplace: str = "US"):
        """
        :param db: 数据库连接对象
        :param http_client: HTTP 客户端（用于爬取竞品数据）
        :param marketplace: 站点标识
        """
        self.db = db
        self.http_client = http_client
        self.marketplace = marketplace

    # ------------------------------------------------------------------
    # 竞品发现
    # ------------------------------------------------------------------
    def find_by_keyword(self, keyword: str, products: list[dict],
                        target_asin: str = None, top_n: int = 20) -> list[dict]:
        """
        从关键词搜索结果中发现竞品
        :param keyword: 搜索关键词
        :param products: 搜索结果产品列表
        :param target_asin: 目标产品 ASIN（排除自身）
        :param top_n: 返回前 N 个竞品
        :return: 竞品列表（含竞争力评分）
        """
        competitors = []

        for product in products:
            asin = product.get("asin") or product.get("product_id", "")
            if target_asin and asin == target_asin:
                continue

            # 计算竞争力评分
            score = self._calculate_competitiveness(product)

            competitors.append({
                "asin": asin,
                "title": product.get("title", ""),
                "price": product.get("price") or product.get("price_current", 0),
                "rating": product.get("rating", 0),
                "review_count": product.get("review_count", 0),
                "bsr_rank": product.get("bsr_rank") or product.get("bsr", 0),
                "monthly_sales": product.get("est_sales_30d") or product.get("monthly_sales", 0),
                "fulfillment": product.get("fulfillment_type") or product.get("fulfillment", ""),
                "main_image": product.get("main_image") or product.get("main_image_url", ""),
                "brand": product.get("brand", ""),
                "competitiveness_score": score,
                "source": "keyword_search",
                "keyword": keyword,
            })

        # 按竞争力评分排序
        competitors.sort(key=lambda x: x["competitiveness_score"], reverse=True)
        return competitors[:top_n]

    def find_by_category(self, category: str, products: list[dict],
                         target_asin: str = None, top_n: int = 20) -> list[dict]:
        """
        从类目排名中发现竞品
        """
        competitors = self.find_by_keyword(category, products, target_asin, top_n)
        for c in competitors:
            c["source"] = "category_ranking"
            c["category"] = category
        return competitors

    # ------------------------------------------------------------------
    # 竞品对比矩阵
    # ------------------------------------------------------------------
    def build_comparison_matrix(self, target: dict,
                                competitors: list[dict]) -> dict:
        """
        构建竞品对比矩阵
        :param target: 目标产品数据
        :param competitors: 竞品列表
        :return: 对比矩阵数据
        """
        all_products = [target] + competitors
        matrix = {
            "target": self._normalize_product(target),
            "competitors": [self._normalize_product(c) for c in competitors],
            "dimensions": {},
            "market_position": {},
            "generated_at": datetime.now().isoformat(),
        }

        # 各维度对比
        prices = [p.get("price") or p.get("price_current", 0) for p in all_products if p.get("price") or p.get("price_current")]
        ratings = [p.get("rating", 0) for p in all_products if p.get("rating")]
        reviews = [p.get("review_count", 0) for p in all_products if p.get("review_count")]
        bsr_ranks = [p.get("bsr_rank") or p.get("bsr", 0) for p in all_products if p.get("bsr_rank") or p.get("bsr")]

        target_price = target.get("price") or target.get("price_current", 0)
        target_rating = target.get("rating", 0)
        target_reviews = target.get("review_count", 0)
        target_bsr = target.get("bsr_rank") or target.get("bsr", 0)

        matrix["dimensions"] = {
            "price": {
                "target": target_price,
                "avg": round(sum(prices) / max(len(prices), 1), 2),
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0,
                "percentile": self._percentile_rank(prices, target_price, reverse=True),
            },
            "rating": {
                "target": target_rating,
                "avg": round(sum(ratings) / max(len(ratings), 1), 2),
                "min": min(ratings) if ratings else 0,
                "max": max(ratings) if ratings else 0,
                "percentile": self._percentile_rank(ratings, target_rating),
            },
            "reviews": {
                "target": target_reviews,
                "avg": round(sum(reviews) / max(len(reviews), 1)),
                "min": min(reviews) if reviews else 0,
                "max": max(reviews) if reviews else 0,
                "percentile": self._percentile_rank(reviews, target_reviews),
            },
            "bsr": {
                "target": target_bsr,
                "avg": round(sum(bsr_ranks) / max(len(bsr_ranks), 1)),
                "min": min(bsr_ranks) if bsr_ranks else 0,
                "max": max(bsr_ranks) if bsr_ranks else 0,
                "percentile": self._percentile_rank(bsr_ranks, target_bsr, reverse=True),
            },
        }

        # 市场定位分析
        matrix["market_position"] = self._analyze_market_position(
            target, competitors
        )

        return matrix

    # ------------------------------------------------------------------
    # 竞争格局分析
    # ------------------------------------------------------------------
    def analyze_competitive_landscape(self, products: list[dict]) -> dict:
        """
        分析竞争格局
        :param products: 产品列表
        :return: 竞争格局分析结果
        """
        if not products:
            return {"error": "无产品数据"}

        result = {
            "total_products": len(products),
            "market_concentration": {},
            "price_distribution": {},
            "rating_distribution": {},
            "fulfillment_distribution": {},
            "brand_analysis": {},
            "entry_barriers": {},
            "opportunities": [],
            "analyzed_at": datetime.now().isoformat(),
        }

        # 市场集中度（品牌）
        brand_counts = {}
        brand_sales = {}
        for p in products:
            brand = p.get("brand", "Unknown") or "Unknown"
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
            sales = p.get("est_sales_30d") or p.get("monthly_sales", 0)
            brand_sales[brand] = brand_sales.get(brand, 0) + (sales or 0)

        total_sales = sum(brand_sales.values())
        top_brands = sorted(brand_sales.items(), key=lambda x: x[1], reverse=True)[:10]

        # HHI 指数（赫芬达尔指数）
        hhi = 0
        if total_sales > 0:
            for brand, sales in brand_sales.items():
                share = (sales / total_sales) * 100
                hhi += share ** 2

        result["market_concentration"] = {
            "hhi_index": round(hhi),
            "concentration_level": (
                "高度集中" if hhi > 2500 else
                "中度集中" if hhi > 1500 else
                "低度集中（竞争充分）"
            ),
            "top_brands": [
                {
                    "brand": brand,
                    "product_count": brand_counts.get(brand, 0),
                    "estimated_sales": sales,
                    "market_share_pct": round(sales / max(total_sales, 1) * 100, 1),
                }
                for brand, sales in top_brands
            ],
            "unique_brands": len(brand_counts),
        }

        # 价格带分布
        prices = [p.get("price") or p.get("price_current", 0) for p in products if p.get("price") or p.get("price_current")]
        if prices:
            price_ranges = self._build_price_ranges(prices)
            result["price_distribution"] = {
                "avg_price": round(sum(prices) / len(prices), 2),
                "median_price": round(sorted(prices)[len(prices) // 2], 2),
                "min_price": round(min(prices), 2),
                "max_price": round(max(prices), 2),
                "ranges": price_ranges,
            }

        # 评分分布
        ratings = [p.get("rating", 0) for p in products if p.get("rating")]
        if ratings:
            rating_buckets = {"4.5+": 0, "4.0-4.5": 0, "3.5-4.0": 0, "3.0-3.5": 0, "<3.0": 0}
            for r in ratings:
                if r >= 4.5:
                    rating_buckets["4.5+"] += 1
                elif r >= 4.0:
                    rating_buckets["4.0-4.5"] += 1
                elif r >= 3.5:
                    rating_buckets["3.5-4.0"] += 1
                elif r >= 3.0:
                    rating_buckets["3.0-3.5"] += 1
                else:
                    rating_buckets["<3.0"] += 1
            result["rating_distribution"] = {
                "avg_rating": round(sum(ratings) / len(ratings), 2),
                "buckets": rating_buckets,
            }

        # Fulfillment 分布
        fba_count = 0
        fbm_count = 0
        amz_count = 0
        for p in products:
            ft = (p.get("fulfillment_type") or p.get("fulfillment", "")).upper()
            if "FBA" in ft:
                fba_count += 1
            elif "FBM" in ft or "MERCHANT" in ft:
                fbm_count += 1
            elif "AMAZON" in ft or "AMZ" in ft:
                amz_count += 1
        result["fulfillment_distribution"] = {
            "FBA": fba_count,
            "FBM": fbm_count,
            "Amazon": amz_count,
            "Other": len(products) - fba_count - fbm_count - amz_count,
        }

        # 进入壁垒评估
        avg_reviews = sum(p.get("review_count", 0) for p in products) / max(len(products), 1)
        avg_rating = sum(p.get("rating", 0) for p in products if p.get("rating")) / max(len(ratings), 1) if ratings else 0
        result["entry_barriers"] = self._assess_entry_barriers(
            avg_reviews, avg_rating, hhi, fba_count / max(len(products), 1)
        )

        # 机会发现
        result["opportunities"] = self._find_opportunities(products, result)

        return result

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _calculate_competitiveness(self, product: dict) -> float:
        """计算单个产品的竞争力评分 (0-100)"""
        score = 0

        # 评分权重 (40%)
        rating = product.get("rating", 0)
        if rating >= 4.5:
            score += 40
        elif rating >= 4.0:
            score += 30
        elif rating >= 3.5:
            score += 20
        elif rating >= 3.0:
            score += 10

        # 评论数权重 (30%)
        reviews = product.get("review_count", 0)
        if reviews >= 1000:
            score += 30
        elif reviews >= 500:
            score += 25
        elif reviews >= 100:
            score += 20
        elif reviews >= 50:
            score += 15
        elif reviews >= 10:
            score += 10

        # BSR 权重 (20%)
        bsr = product.get("bsr_rank") or product.get("bsr", 0)
        if bsr and bsr > 0:
            if bsr <= 1000:
                score += 20
            elif bsr <= 5000:
                score += 15
            elif bsr <= 20000:
                score += 10
            elif bsr <= 50000:
                score += 5

        # FBA 加分 (10%)
        ft = (product.get("fulfillment_type") or product.get("fulfillment", "")).upper()
        if "FBA" in ft or "AMAZON" in ft:
            score += 10

        return min(score, 100)

    def _normalize_product(self, product: dict) -> dict:
        """标准化产品数据字段"""
        return {
            "asin": product.get("asin") or product.get("product_id", ""),
            "title": product.get("title", ""),
            "price": product.get("price") or product.get("price_current", 0),
            "rating": product.get("rating", 0),
            "review_count": product.get("review_count", 0),
            "bsr_rank": product.get("bsr_rank") or product.get("bsr", 0),
            "monthly_sales": product.get("est_sales_30d") or product.get("monthly_sales", 0),
            "fulfillment": product.get("fulfillment_type") or product.get("fulfillment", ""),
            "brand": product.get("brand", ""),
            "main_image": product.get("main_image") or product.get("main_image_url", ""),
        }

    @staticmethod
    def _percentile_rank(values: list, target: float, reverse: bool = False) -> int:
        """
        计算目标值在列表中的百分位排名
        :param reverse: True 表示值越小越好（如价格、BSR）
        """
        if not values or target is None:
            return 50
        if reverse:
            count = sum(1 for v in values if v >= target)
        else:
            count = sum(1 for v in values if v <= target)
        return round(count / len(values) * 100)

    def _analyze_market_position(self, target: dict,
                                  competitors: list[dict]) -> dict:
        """分析目标产品的市场定位"""
        all_products = [target] + competitors
        target_price = target.get("price") or target.get("price_current", 0)
        prices = [p.get("price") or p.get("price_current", 0) for p in all_products if p.get("price") or p.get("price_current")]
        avg_price = sum(prices) / max(len(prices), 1) if prices else 0

        # 价格定位
        if avg_price > 0:
            price_ratio = target_price / avg_price
            if price_ratio > 1.2:
                price_position = "premium"
            elif price_ratio > 0.9:
                price_position = "mid_range"
            else:
                price_position = "budget"
        else:
            price_position = "unknown"

        # 竞争力排名
        all_scores = []
        for p in all_products:
            score = self._calculate_competitiveness(p)
            asin = p.get("asin") or p.get("product_id", "")
            all_scores.append({"asin": asin, "score": score})
        all_scores.sort(key=lambda x: x["score"], reverse=True)

        target_asin = target.get("asin") or target.get("product_id", "")
        target_rank = next(
            (i + 1 for i, s in enumerate(all_scores) if s["asin"] == target_asin),
            len(all_scores)
        )

        # 优劣势分析
        strengths = []
        weaknesses = []

        target_rating = target.get("rating", 0)
        avg_rating = sum(p.get("rating", 0) for p in competitors if p.get("rating")) / max(len(competitors), 1)
        if target_rating > avg_rating + 0.2:
            strengths.append(f"评分优势 ({target_rating} vs 均值 {avg_rating:.1f})")
        elif target_rating < avg_rating - 0.2:
            weaknesses.append(f"评分劣势 ({target_rating} vs 均值 {avg_rating:.1f})")

        target_reviews = target.get("review_count", 0)
        avg_reviews = sum(p.get("review_count", 0) for p in competitors) / max(len(competitors), 1)
        if target_reviews > avg_reviews * 1.5:
            strengths.append(f"评论数优势 ({target_reviews} vs 均值 {avg_reviews:.0f})")
        elif target_reviews < avg_reviews * 0.5:
            weaknesses.append(f"评论数不足 ({target_reviews} vs 均值 {avg_reviews:.0f})")

        if price_position == "budget":
            strengths.append("价格竞争力强")
        elif price_position == "premium":
            weaknesses.append("价格偏高，需要差异化支撑")

        return {
            "price_position": price_position,
            "competitiveness_rank": target_rank,
            "total_competitors": len(competitors),
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    @staticmethod
    def _build_price_ranges(prices: list) -> list[dict]:
        """构建价格带分布"""
        if not prices:
            return []

        min_p = min(prices)
        max_p = max(prices)
        range_size = max((max_p - min_p) / 5, 1)

        ranges = []
        for i in range(5):
            low = round(min_p + i * range_size, 2)
            high = round(min_p + (i + 1) * range_size, 2)
            count = sum(1 for p in prices if low <= p < high or (i == 4 and p == high))
            ranges.append({
                "label": f"${low:.0f}-${high:.0f}",
                "low": low,
                "high": high,
                "count": count,
                "percentage": round(count / len(prices) * 100, 1),
            })
        return ranges

    @staticmethod
    def _assess_entry_barriers(avg_reviews: float, avg_rating: float,
                                hhi: float, fba_ratio: float) -> dict:
        """评估市场进入壁垒"""
        barrier_score = 0
        factors = []

        # 评论壁垒
        if avg_reviews > 500:
            barrier_score += 30
            factors.append({"factor": "评论壁垒", "level": "高",
                            "detail": f"平均评论数 {avg_reviews:.0f}，新品追赶困难"})
        elif avg_reviews > 100:
            barrier_score += 15
            factors.append({"factor": "评论壁垒", "level": "中",
                            "detail": f"平均评论数 {avg_reviews:.0f}，需要积累期"})
        else:
            factors.append({"factor": "评论壁垒", "level": "低",
                            "detail": f"平均评论数 {avg_reviews:.0f}，新品容易切入"})

        # 品牌集中度壁垒
        if hhi > 2500:
            barrier_score += 25
            factors.append({"factor": "品牌集中度", "level": "高",
                            "detail": "市场被少数品牌垄断"})
        elif hhi > 1500:
            barrier_score += 15
            factors.append({"factor": "品牌集中度", "level": "中",
                            "detail": "市场中度集中"})
        else:
            factors.append({"factor": "品牌集中度", "level": "低",
                            "detail": "市场竞争充分，品牌分散"})

        # 质量壁垒
        if avg_rating > 4.3:
            barrier_score += 20
            factors.append({"factor": "质量壁垒", "level": "高",
                            "detail": f"平均评分 {avg_rating:.1f}，质量要求高"})
        elif avg_rating > 4.0:
            barrier_score += 10
            factors.append({"factor": "质量壁垒", "level": "中",
                            "detail": f"平均评分 {avg_rating:.1f}"})
        else:
            factors.append({"factor": "质量壁垒", "level": "低",
                            "detail": f"平均评分 {avg_rating:.1f}，有提升空间"})

        # FBA 壁垒
        if fba_ratio > 0.8:
            barrier_score += 15
            factors.append({"factor": "FBA 壁垒", "level": "高",
                            "detail": f"FBA 占比 {fba_ratio:.0%}，必须使用 FBA"})
        elif fba_ratio > 0.5:
            barrier_score += 8
            factors.append({"factor": "FBA 壁垒", "level": "中",
                            "detail": f"FBA 占比 {fba_ratio:.0%}"})

        # 总体评估
        if barrier_score >= 60:
            overall = "高"
            recommendation = "进入壁垒较高，建议寻找差异化切入点或选择其他品类"
        elif barrier_score >= 35:
            overall = "中"
            recommendation = "进入壁垒适中，需要一定资金和运营能力"
        else:
            overall = "低"
            recommendation = "进入壁垒较低，适合新卖家切入"

        return {
            "overall_level": overall,
            "barrier_score": barrier_score,
            "max_score": 90,
            "factors": factors,
            "recommendation": recommendation,
        }

    @staticmethod
    def _find_opportunities(products: list[dict], analysis: dict) -> list[str]:
        """发现市场机会"""
        opportunities = []

        # 价格空白带
        price_dist = analysis.get("price_distribution", {})
        ranges = price_dist.get("ranges", [])
        for r in ranges:
            if r.get("count", 0) == 0 and r.get("low", 0) > 0:
                opportunities.append(
                    f"价格空白带 {r['label']}：该价格区间无竞品，可能是差异化定价机会"
                )

        # 低评分竞品多 = 质量提升机会
        rating_dist = analysis.get("rating_distribution", {})
        buckets = rating_dist.get("buckets", {})
        low_rating_count = buckets.get("<3.0", 0) + buckets.get("3.0-3.5", 0)
        if low_rating_count > len(products) * 0.3:
            opportunities.append(
                f"质量提升机会：{low_rating_count} 个竞品评分低于 3.5，通过提升产品质量可获得竞争优势"
            )

        # FBM 占比高 = FBA 配送优势
        fulfillment = analysis.get("fulfillment_distribution", {})
        fbm_count = fulfillment.get("FBM", 0)
        if fbm_count > len(products) * 0.4:
            opportunities.append(
                f"配送优势机会：{fbm_count} 个竞品使用 FBM，使用 FBA 可获得配送和排名优势"
            )

        # 市场分散 = 品牌机会
        concentration = analysis.get("market_concentration", {})
        if concentration.get("hhi_index", 0) < 1000:
            opportunities.append(
                "品牌建设机会：市场高度分散，通过品牌化运营可快速建立市场地位"
            )

        # 评论数低 = 新品友好
        avg_reviews = sum(p.get("review_count", 0) for p in products) / max(len(products), 1)
        if avg_reviews < 100:
            opportunities.append(
                f"新品友好市场：平均评论数仅 {avg_reviews:.0f}，新品容易获得曝光和排名"
            )

        return opportunities
