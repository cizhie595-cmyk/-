"""
Amazon 大盘与类目分析模块

针对 Amazon 平台的类目分析：
  - Google Trends 趋势数据集成
  - 类目 GMV 预估
  - 竞争格局分析（垄断度、品牌集中度）
  - 季节性分析
  - 新品机会窗口识别
"""

import re
import json
import math
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()


class AmazonCategoryAnalyzer:
    """
    Amazon 类目分析器

    从宏观层面评估目标类目的市场容量、竞争格局和趋势走向，
    帮助卖家判断是否值得进入该类目。
    """

    def __init__(self, ai_client=None, ai_model: str = "gpt-4.1-mini"):
        self.ai_client = ai_client
        self.ai_model = ai_model

    def analyze_category(self, products: list[dict],
                         keyword: str,
                         trends_data: dict = None) -> dict:
        """
        对一个类目进行全面分析。

        :param products: 该类目的产品列表（搜索结果前48-96个）
        :param keyword: 搜索关键词
        :param trends_data: Google Trends 数据（可选）
        :return: 类目分析报告
        """
        logger.info(f"[类目分析] 开始分析: {keyword} | 产品数: {len(products)}")

        report = {
            "keyword": keyword,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "product_count": len(products),
        }

        # 1. 市场容量预估
        report["market_size"] = self._estimate_market_size(products)

        # 2. 竞争格局分析
        report["competition"] = self._analyze_competition(products)

        # 3. 价格分析
        report["pricing"] = self._analyze_pricing(products)

        # 4. 评论分析
        report["review_landscape"] = self._analyze_review_landscape(products)

        # 5. 品牌集中度
        report["brand_concentration"] = self._analyze_brand_concentration(products)

        # 6. 物流方式分布
        report["fulfillment_distribution"] = self._analyze_fulfillment(products)

        # 7. 趋势分析（Google Trends）
        if trends_data:
            report["trends"] = self._analyze_trends(trends_data)
        else:
            report["trends"] = {"status": "no_data", "note": "请配置 Google Trends 数据源"}

        # 8. 季节性分析
        report["seasonality"] = self._analyze_seasonality(products, trends_data)

        # 9. 新品机会窗口
        report["opportunity"] = self._identify_opportunities(products, report)

        # 10. 垄断度评估
        report["monopoly_index"] = self._calculate_monopoly_index(products)

        # 11. AI 综合评估
        if self.ai_client:
            report["ai_summary"] = self._ai_summarize(report, keyword)

        logger.info(f"[类目分析] {keyword} 分析完成")
        return report

    # ================================================================
    # 市场容量预估
    # ================================================================

    def _estimate_market_size(self, products: list[dict]) -> dict:
        """
        预估类目市场容量（月 GMV）。

        方法: 基于 BSR 排名和价格预估每个产品的月销量，
        然后汇总得到类目总 GMV。
        """
        total_monthly_sales = 0
        total_monthly_revenue = 0
        estimated_products = 0

        for product in products:
            bsr = product.get("bsr", 0)
            price = product.get("price", 0) or 0
            monthly_sales = product.get("estimated_monthly_sales", 0)

            # 如果没有预估销量，基于 BSR 估算
            if not monthly_sales and bsr > 0:
                monthly_sales = self._bsr_to_sales(bsr)

            if monthly_sales > 0 and price > 0:
                revenue = monthly_sales * price
                total_monthly_sales += monthly_sales
                total_monthly_revenue += revenue
                estimated_products += 1

        # 头部产品只是冰山一角，实际市场更大
        # 经验系数: 搜索结果前48个约占类目总销量的 30-50%
        market_multiplier = 2.5  # 保守估计

        return {
            "sampled_products": estimated_products,
            "sampled_monthly_sales": total_monthly_sales,
            "sampled_monthly_revenue": round(total_monthly_revenue, 2),
            "estimated_total_monthly_gmv": round(total_monthly_revenue * market_multiplier, 2),
            "estimated_total_annual_gmv": round(total_monthly_revenue * market_multiplier * 12, 2),
            "avg_monthly_sales_per_product": round(total_monthly_sales / max(estimated_products, 1)),
            "avg_price": round(total_monthly_revenue / max(total_monthly_sales, 1), 2) if total_monthly_sales > 0 else 0,
            "market_size_tier": self._classify_market_size(total_monthly_revenue * market_multiplier),
        }

    @staticmethod
    def _bsr_to_sales(bsr: int) -> int:
        """BSR 转月销量（经验公式）"""
        if bsr <= 0:
            return 0
        return max(1, int(120000 * (bsr ** -0.75)))

    @staticmethod
    def _classify_market_size(monthly_gmv: float) -> str:
        """市场规模分级"""
        if monthly_gmv >= 10_000_000:
            return "超大型市场(>$10M/月)"
        elif monthly_gmv >= 1_000_000:
            return "大型市场($1M-$10M/月)"
        elif monthly_gmv >= 100_000:
            return "中型市场($100K-$1M/月)"
        elif monthly_gmv >= 10_000:
            return "小型市场($10K-$100K/月)"
        else:
            return "微型市场(<$10K/月)"

    # ================================================================
    # 竞争格局分析
    # ================================================================

    def _analyze_competition(self, products: list[dict]) -> dict:
        """分析竞争格局"""
        if not products:
            return {}

        review_counts = [p.get("review_count", 0) or 0 for p in products]
        ratings = [p.get("rating", 0) or 0 for p in products if p.get("rating")]
        bsr_values = [p.get("bsr", 0) for p in products if p.get("bsr", 0) > 0]

        # 头部竞品分析（前10名）
        top_10 = products[:10]
        top_10_reviews = [p.get("review_count", 0) or 0 for p in top_10]
        top_10_avg_reviews = sum(top_10_reviews) / max(len(top_10_reviews), 1)

        # 竞争强度评估
        competition_level = self._assess_competition_level(
            avg_reviews=sum(review_counts) / max(len(review_counts), 1),
            top_10_avg_reviews=top_10_avg_reviews,
            avg_rating=sum(ratings) / max(len(ratings), 1) if ratings else 0,
        )

        return {
            "total_products_analyzed": len(products),
            "avg_review_count": round(sum(review_counts) / max(len(review_counts), 1)),
            "median_review_count": sorted(review_counts)[len(review_counts) // 2] if review_counts else 0,
            "max_review_count": max(review_counts) if review_counts else 0,
            "avg_rating": round(sum(ratings) / max(len(ratings), 1), 2) if ratings else 0,
            "top_10_avg_reviews": round(top_10_avg_reviews),
            "top_10_avg_rating": round(
                sum(p.get("rating", 0) or 0 for p in top_10) / max(len(top_10), 1), 2
            ),
            "competition_level": competition_level,
            "new_entry_difficulty": self._assess_entry_difficulty(top_10_avg_reviews, competition_level),
        }

    @staticmethod
    def _assess_competition_level(avg_reviews: float, top_10_avg_reviews: float,
                                   avg_rating: float) -> str:
        """评估竞争强度"""
        score = 0
        if top_10_avg_reviews > 5000:
            score += 3
        elif top_10_avg_reviews > 1000:
            score += 2
        elif top_10_avg_reviews > 300:
            score += 1

        if avg_reviews > 500:
            score += 2
        elif avg_reviews > 100:
            score += 1

        if avg_rating > 4.3:
            score += 1

        if score >= 5:
            return "极高竞争"
        elif score >= 3:
            return "高竞争"
        elif score >= 2:
            return "中等竞争"
        else:
            return "低竞争"

    @staticmethod
    def _assess_entry_difficulty(top_10_avg_reviews: float,
                                  competition_level: str) -> dict:
        """评估新品进入难度"""
        if competition_level in ("极高竞争", "高竞争"):
            return {
                "level": "困难",
                "estimated_reviews_needed": int(top_10_avg_reviews * 0.3),
                "estimated_time_months": "12-18",
                "estimated_ppc_budget": "$3000-$8000/月",
                "recommendation": "需要差异化产品和充足资金，不建议新手进入",
            }
        elif competition_level == "中等竞争":
            return {
                "level": "中等",
                "estimated_reviews_needed": int(top_10_avg_reviews * 0.2),
                "estimated_time_months": "6-12",
                "estimated_ppc_budget": "$1000-$3000/月",
                "recommendation": "有机会，但需要产品差异化和持续运营",
            }
        else:
            return {
                "level": "容易",
                "estimated_reviews_needed": max(50, int(top_10_avg_reviews * 0.15)),
                "estimated_time_months": "3-6",
                "estimated_ppc_budget": "$500-$1500/月",
                "recommendation": "新品友好，建议快速进入抢占市场",
            }

    # ================================================================
    # 价格分析
    # ================================================================

    def _analyze_pricing(self, products: list[dict]) -> dict:
        """分析价格分布"""
        prices = [p.get("price", 0) for p in products if p.get("price") and p["price"] > 0]
        if not prices:
            return {}

        prices.sort()
        n = len(prices)

        # 价格区间分布
        ranges = {}
        for price in prices:
            if price < 10:
                bucket = "$0-$10"
            elif price < 20:
                bucket = "$10-$20"
            elif price < 30:
                bucket = "$20-$30"
            elif price < 50:
                bucket = "$30-$50"
            elif price < 100:
                bucket = "$50-$100"
            else:
                bucket = "$100+"
            ranges[bucket] = ranges.get(bucket, 0) + 1

        # 找最佳价格区间（产品最多的区间）
        best_range = max(ranges.items(), key=lambda x: x[1]) if ranges else ("N/A", 0)

        return {
            "min_price": prices[0],
            "max_price": prices[-1],
            "avg_price": round(sum(prices) / n, 2),
            "median_price": prices[n // 2],
            "price_25th": prices[n // 4],
            "price_75th": prices[3 * n // 4],
            "price_distribution": ranges,
            "recommended_price_range": best_range[0],
            "sweet_spot": f"${prices[n//4]:.2f} - ${prices[3*n//4]:.2f}",
        }

    # ================================================================
    # 评论分析
    # ================================================================

    def _analyze_review_landscape(self, products: list[dict]) -> dict:
        """分析评论整体状况"""
        review_counts = [p.get("review_count", 0) or 0 for p in products]
        ratings = [p.get("rating", 0) or 0 for p in products if p.get("rating")]

        # 评论数分布
        low_reviews = sum(1 for r in review_counts if r < 50)
        mid_reviews = sum(1 for r in review_counts if 50 <= r < 500)
        high_reviews = sum(1 for r in review_counts if r >= 500)

        return {
            "total_reviews_in_category": sum(review_counts),
            "avg_reviews": round(sum(review_counts) / max(len(review_counts), 1)),
            "avg_rating": round(sum(ratings) / max(len(ratings), 1), 2) if ratings else 0,
            "products_under_50_reviews": low_reviews,
            "products_50_to_500_reviews": mid_reviews,
            "products_over_500_reviews": high_reviews,
            "low_review_percentage": round(low_reviews / max(len(products), 1) * 100, 1),
            "review_gap_opportunity": low_reviews > len(products) * 0.3,
        }

    # ================================================================
    # 品牌集中度
    # ================================================================

    def _analyze_brand_concentration(self, products: list[dict]) -> dict:
        """分析品牌集中度"""
        brand_counts = {}
        brand_sales = {}

        for product in products:
            brand = product.get("brand", "Unknown") or "Unknown"
            brand_counts[brand] = brand_counts.get(brand, 0) + 1

            sales = product.get("estimated_monthly_sales", 0)
            brand_sales[brand] = brand_sales.get(brand, 0) + sales

        # 按产品数量排序
        sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
        total = len(products)

        # 前3品牌占比
        top_3_count = sum(count for _, count in sorted_brands[:3])
        top_3_pct = round(top_3_count / max(total, 1) * 100, 1)

        # HHI 指数（赫芬达尔指数，衡量市场集中度）
        hhi = sum((count / total * 100) ** 2 for _, count in sorted_brands) if total > 0 else 0

        concentration_level = "高度集中" if hhi > 2500 else "中度集中" if hhi > 1500 else "分散"

        return {
            "total_brands": len(brand_counts),
            "top_brands": [
                {"brand": brand, "count": count, "share": f"{count/max(total,1)*100:.1f}%"}
                for brand, count in sorted_brands[:10]
            ],
            "top_3_share": f"{top_3_pct}%",
            "hhi_index": round(hhi, 1),
            "concentration_level": concentration_level,
            "has_dominant_brand": top_3_pct > 50,
            "brand_diversity_score": min(len(brand_counts) / max(total, 1) * 100, 100),
        }

    # ================================================================
    # 物流方式分布
    # ================================================================

    def _analyze_fulfillment(self, products: list[dict]) -> dict:
        """分析物流方式分布"""
        fba_count = 0
        fbm_count = 0
        sfp_count = 0
        unknown_count = 0

        for product in products:
            fulfillment = product.get("fulfillment", {})
            f_type = fulfillment.get("type", "unknown") if isinstance(fulfillment, dict) else str(fulfillment)

            if f_type == "FBA":
                fba_count += 1
            elif f_type == "FBM":
                fbm_count += 1
            elif f_type == "SFP":
                sfp_count += 1
            else:
                unknown_count += 1

        total = len(products) or 1

        return {
            "fba_count": fba_count,
            "fba_percentage": round(fba_count / total * 100, 1),
            "fbm_count": fbm_count,
            "fbm_percentage": round(fbm_count / total * 100, 1),
            "sfp_count": sfp_count,
            "sfp_percentage": round(sfp_count / total * 100, 1),
            "recommendation": "FBA" if fba_count > fbm_count else "FBM",
        }

    # ================================================================
    # 趋势分析
    # ================================================================

    def _analyze_trends(self, trends_data: dict) -> dict:
        """分析 Google Trends 数据"""
        timeline = trends_data.get("timeline", [])
        if not timeline:
            return {"status": "no_timeline_data"}

        values = [point.get("value", 0) for point in timeline]
        if not values:
            return {"status": "empty_values"}

        # 近期趋势（最近3个月 vs 前3个月）
        recent = values[-12:] if len(values) >= 12 else values[-len(values)//2:]
        earlier = values[-24:-12] if len(values) >= 24 else values[:len(values)//2]

        recent_avg = sum(recent) / max(len(recent), 1)
        earlier_avg = sum(earlier) / max(len(earlier), 1)

        trend_direction = "上升" if recent_avg > earlier_avg * 1.1 else \
                         "下降" if recent_avg < earlier_avg * 0.9 else "稳定"

        growth_rate = ((recent_avg - earlier_avg) / max(earlier_avg, 1)) * 100

        return {
            "current_interest": values[-1] if values else 0,
            "peak_interest": max(values),
            "avg_interest": round(sum(values) / len(values), 1),
            "trend_direction": trend_direction,
            "growth_rate": f"{growth_rate:+.1f}%",
            "is_trending_up": growth_rate > 10,
            "data_points": len(values),
        }

    # ================================================================
    # 季节性分析
    # ================================================================

    def _analyze_seasonality(self, products: list[dict],
                              trends_data: dict = None) -> dict:
        """分析类目的季节性特征"""
        result = {"is_seasonal": False, "peak_months": [], "low_months": []}

        if trends_data and trends_data.get("timeline"):
            timeline = trends_data["timeline"]
            # 按月份聚合
            monthly_avg = {}
            for point in timeline:
                month = point.get("date", "")[:7]  # YYYY-MM
                if len(month) >= 7:
                    m = int(month.split("-")[1])
                    if m not in monthly_avg:
                        monthly_avg[m] = []
                    monthly_avg[m].append(point.get("value", 0))

            if monthly_avg:
                month_scores = {
                    m: sum(vals) / len(vals) for m, vals in monthly_avg.items()
                }
                avg_score = sum(month_scores.values()) / len(month_scores)

                # 判断季节性（最高月份是最低月份的2倍以上）
                if month_scores:
                    max_val = max(month_scores.values())
                    min_val = min(month_scores.values()) or 1
                    result["is_seasonal"] = max_val / min_val > 2

                    result["peak_months"] = [
                        m for m, v in month_scores.items() if v > avg_score * 1.3
                    ]
                    result["low_months"] = [
                        m for m, v in month_scores.items() if v < avg_score * 0.7
                    ]
                    result["seasonality_ratio"] = round(max_val / min_val, 2)

        return result

    # ================================================================
    # 垄断度评估
    # ================================================================

    def _calculate_monopoly_index(self, products: list[dict]) -> dict:
        """
        计算类目垄断度指数。

        综合考虑:
          - 头部品牌市场份额
          - 评论数集中度
          - BSR 分布均匀度
        """
        if not products:
            return {"index": 0, "level": "无数据"}

        # 评论数集中度（前3名评论占比）
        review_counts = sorted(
            [p.get("review_count", 0) or 0 for p in products], reverse=True
        )
        total_reviews = sum(review_counts) or 1
        top_3_review_share = sum(review_counts[:3]) / total_reviews

        # 品牌集中度
        brand_counts = {}
        for p in products:
            brand = p.get("brand", "Unknown") or "Unknown"
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        total = len(products) or 1
        sorted_brands = sorted(brand_counts.values(), reverse=True)
        top_brand_share = sorted_brands[0] / total if sorted_brands else 0

        # 综合垄断指数 (0-100)
        index = (top_3_review_share * 50 + top_brand_share * 50) * 100

        if index >= 70:
            level = "高度垄断"
            advice = "头部品牌占据绝对优势，新品进入风险极高"
        elif index >= 40:
            level = "中度垄断"
            advice = "存在强势品牌但仍有差异化空间"
        else:
            level = "竞争分散"
            advice = "市场分散，新品有较好的进入机会"

        return {
            "index": round(index, 1),
            "level": level,
            "top_3_review_share": f"{top_3_review_share*100:.1f}%",
            "top_brand_share": f"{top_brand_share*100:.1f}%",
            "advice": advice,
        }

    # ================================================================
    # 新品机会识别
    # ================================================================

    def _identify_opportunities(self, products: list[dict],
                                 report: dict) -> dict:
        """识别新品进入机会"""
        opportunities = []
        risk_factors = []

        competition = report.get("competition", {})
        pricing = report.get("pricing", {})
        brand_conc = report.get("brand_concentration", {})
        review_land = report.get("review_landscape", {})

        # 机会信号
        if review_land.get("low_review_percentage", 0) > 30:
            opportunities.append("超过30%的产品评论数低于50，新品有机会快速上位")

        if competition.get("competition_level") in ("低竞争", "中等竞争"):
            opportunities.append(f"竞争强度为{competition['competition_level']}，适合新品进入")

        if not brand_conc.get("has_dominant_brand"):
            opportunities.append("无绝对主导品牌，市场格局未定")

        avg_rating = competition.get("avg_rating", 0)
        if avg_rating and avg_rating < 4.2:
            opportunities.append(f"类目平均评分仅{avg_rating}，产品质量有提升空间")

        # 风险因素
        if competition.get("competition_level") == "极高竞争":
            risk_factors.append("竞争极其激烈，需要大量资金和差异化产品")

        if brand_conc.get("has_dominant_brand"):
            risk_factors.append("存在主导品牌，新品可能面临品牌壁垒")

        monopoly = report.get("monopoly_index", {})
        if monopoly.get("index", 0) > 60:
            risk_factors.append(f"垄断指数{monopoly['index']}，头部效应明显")

        # 综合评分
        opportunity_score = len(opportunities) * 20 - len(risk_factors) * 15
        opportunity_score = max(0, min(100, 50 + opportunity_score))

        return {
            "opportunity_score": opportunity_score,
            "grade": "A" if opportunity_score >= 80 else "B" if opportunity_score >= 60 else "C" if opportunity_score >= 40 else "D",
            "opportunities": opportunities,
            "risk_factors": risk_factors,
            "recommendation": "建议进入" if opportunity_score >= 60 else "谨慎评估" if opportunity_score >= 40 else "不建议进入",
        }

    # ================================================================
    # AI 综合评估
    # ================================================================

    def _ai_summarize(self, report: dict, keyword: str) -> str:
        """使用 AI 生成类目分析总结"""
        if not self.ai_client:
            return ""

        prompt = f"""You are an Amazon market analyst. Based on the following category analysis data, provide a concise executive summary in Chinese (300 words max).

Keyword: {keyword}
Market Size: {json.dumps(report.get('market_size', {}), ensure_ascii=False)}
Competition: {json.dumps(report.get('competition', {}), ensure_ascii=False)}
Pricing: {json.dumps(report.get('pricing', {}), ensure_ascii=False)}
Brand Concentration: {json.dumps(report.get('brand_concentration', {}), ensure_ascii=False)}
Monopoly Index: {json.dumps(report.get('monopoly_index', {}), ensure_ascii=False)}
Opportunity: {json.dumps(report.get('opportunity', {}), ensure_ascii=False)}

Provide:
1. Market overview (1-2 sentences)
2. Key findings (3-4 bullet points)
3. Entry recommendation with reasoning
4. Suggested product strategy if entering"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[类目分析] AI 总结失败: {e}")
            return ""


class GoogleTrendsClient:
    """
    Google Trends 数据获取客户端

    通过非官方 API 获取搜索趋势数据。
    注意: Google 没有官方 Trends API，此模块使用 pytrends 库。
    """

    def __init__(self, geo: str = "US", language: str = "en-US"):
        self.geo = geo
        self.language = language

    def get_interest_over_time(self, keyword: str,
                                timeframe: str = "today 12-m") -> dict:
        """
        获取关键词的搜索兴趣趋势。

        :param keyword: 搜索关键词
        :param timeframe: 时间范围 (today 12-m / today 5-y / 2023-01-01 2024-01-01)
        :return: 趋势数据
        """
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl=self.language, tz=360)
            pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=self.geo)

            df = pytrends.interest_over_time()

            if df.empty:
                return {"keyword": keyword, "timeline": [], "status": "no_data"}

            timeline = []
            for date, row in df.iterrows():
                timeline.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "value": int(row[keyword]),
                })

            return {
                "keyword": keyword,
                "geo": self.geo,
                "timeframe": timeframe,
                "timeline": timeline,
                "status": "success",
            }

        except ImportError:
            logger.error("[GoogleTrends] pytrends 未安装，请运行: pip install pytrends")
            return {"keyword": keyword, "timeline": [], "status": "pytrends_not_installed"}
        except Exception as e:
            logger.error(f"[GoogleTrends] 获取趋势数据失败: {e}")
            return {"keyword": keyword, "timeline": [], "status": "error", "error": str(e)}

    def get_related_queries(self, keyword: str) -> dict:
        """获取相关搜索词"""
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl=self.language, tz=360)
            pytrends.build_payload([keyword], cat=0, timeframe="today 12-m", geo=self.geo)

            related = pytrends.related_queries()
            result = {"keyword": keyword, "top": [], "rising": []}

            if keyword in related:
                top_df = related[keyword].get("top")
                rising_df = related[keyword].get("rising")

                if top_df is not None:
                    result["top"] = top_df.to_dict("records")
                if rising_df is not None:
                    result["rising"] = rising_df.to_dict("records")

            return result

        except Exception as e:
            logger.error(f"[GoogleTrends] 获取相关搜索词失败: {e}")
            return {"keyword": keyword, "top": [], "rising": []}
