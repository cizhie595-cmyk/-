"""
Coupang 选品系统 - 类目趋势分析模块
功能:
  1. Naver 搜索趋势分析
  2. Coupang 站内趋势分析
  3. 月/年 GMV 预估
  4. 垄断程度分析（Top1/3/10 销量占比）
  5. 新品占比分析
"""

import re
import json
from typing import Optional
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t, get_language

logger = get_logger()

# Naver DataLab API（需要API Key）
NAVER_TREND_API = "https://openapi.naver.com/v1/datalab/search"


class CategoryAnalyzer:
    """
    类目趋势分析器
    综合 Naver 搜索趋势 + Coupang 站内数据，评估市场机会
    """

    def __init__(self, http_client: Optional[HttpClient] = None, ai_client=None,
                 naver_client_id: str = None, naver_client_secret: str = None):
        self.client = http_client or HttpClient()
        self.ai_client = ai_client
        self.naver_client_id = naver_client_id
        self.naver_client_secret = naver_client_secret

    def analyze_category(self, keyword: str, products: list[dict],
                         daily_stats: dict = None) -> dict:
        """
        对类目进行全面分析

        :param keyword: 类目关键词
        :param products: 该类目下的产品列表
        :param daily_stats: 产品运营数据
        :return: 类目分析结果
        """
        result = {
            "keyword": keyword,
            "product_count": len(products),
        }

        # 1. Naver 搜索趋势
        result["naver_trend"] = self._get_naver_trend(keyword)

        # 2. 体量预估 (GMV)
        result["gmv_estimate"] = self._estimate_gmv(products, daily_stats)

        # 3. 垄断程度
        result["monopoly_analysis"] = self._analyze_monopoly(products, daily_stats)

        # 4. 新品占比
        result["new_product_analysis"] = self._analyze_new_products(products)

        # 5. 价格分布
        result["price_distribution"] = self._analyze_price_distribution(products)

        # 6. 配送方式分布
        result["delivery_distribution"] = self._analyze_delivery_distribution(products)

        # 7. AI 综合评估
        if self.ai_client:
            result["ai_assessment"] = self._ai_market_assessment(keyword, result)

        return result

    def _get_naver_trend(self, keyword: str) -> dict:
        """
        获取 Naver 搜索趋势数据

        使用 Naver DataLab API
        """
        if not self.naver_client_id or not self.naver_client_secret:
            logger.debug("Naver API credentials not configured, skipping trend data")
            return {"available": False, "reason": "Naver API not configured"}

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        headers = {
            "X-Naver-Client-Id": self.naver_client_id,
            "X-Naver-Client-Secret": self.naver_client_secret,
            "Content-Type": "application/json",
        }

        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "month",
            "keywordGroups": [
                {"groupName": keyword, "keywords": [keyword]}
            ],
        }

        try:
            resp = self.client.session.post(
                NAVER_TREND_API,
                json=body,
                headers=headers,
                timeout=15,
            )

            if resp and resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [{}])[0]
                trend_data = results.get("data", [])

                # 计算趋势方向
                if len(trend_data) >= 3:
                    recent = sum(d.get("ratio", 0) for d in trend_data[-3:]) / 3
                    earlier = sum(d.get("ratio", 0) for d in trend_data[:3]) / 3
                    if recent > earlier * 1.1:
                        trend_direction = "rising"
                    elif recent < earlier * 0.9:
                        trend_direction = "declining"
                    else:
                        trend_direction = "stable"
                else:
                    trend_direction = "unknown"

                return {
                    "available": True,
                    "monthly_data": trend_data,
                    "trend_direction": trend_direction,
                    "latest_score": trend_data[-1].get("ratio", 0) if trend_data else 0,
                }

        except Exception as e:
            logger.error(f"Naver trend API error: {e}")

        return {"available": False, "reason": "API request failed"}

    def _estimate_gmv(self, products: list[dict], daily_stats: dict = None) -> dict:
        """
        预估类目 GMV

        方法: 基于已知产品的销量和价格推算
        """
        if not daily_stats:
            # 无运营数据时，基于评论数粗略估算
            total_reviews = sum(p.get("review_count", 0) for p in products)
            avg_price = self._safe_avg([p.get("price", 0) for p in products if p.get("price")])

            # 经验公式: 月销量 ≈ 评论数 × 评论转化系数(约5-10%)
            estimated_monthly_sales = total_reviews * 0.07
            monthly_gmv = estimated_monthly_sales * avg_price

            return {
                "method": "review_estimation",
                "monthly_gmv_krw": round(monthly_gmv, 0),
                "yearly_gmv_krw": round(monthly_gmv * 12, 0),
                "avg_price_krw": round(avg_price, 0),
                "confidence": "low",
            }

        # 有运营数据时，基于实际销量计算
        total_monthly_revenue = 0
        product_revenues = []

        for product in products:
            pid = product.get("coupang_product_id", "")
            stats = daily_stats.get(pid, [])
            if stats:
                monthly_rev = sum(d.get("daily_revenue", 0) for d in stats[-30:])
                total_monthly_revenue += monthly_rev
                product_revenues.append(monthly_rev)

        return {
            "method": "actual_stats",
            "monthly_gmv_krw": round(total_monthly_revenue, 0),
            "yearly_gmv_krw": round(total_monthly_revenue * 12, 0),
            "avg_product_revenue_krw": round(
                sum(product_revenues) / max(len(product_revenues), 1), 0
            ),
            "products_with_data": len(product_revenues),
            "confidence": "high" if len(product_revenues) >= 10 else "medium",
        }

    def _analyze_monopoly(self, products: list[dict], daily_stats: dict = None) -> dict:
        """
        分析垄断程度

        指标: Top1/3/10 销量占比
        """
        # 获取每个产品的销量
        sales_data = []
        for p in products:
            pid = p.get("coupang_product_id", "")
            if daily_stats and pid in daily_stats:
                total_sales = sum(d.get("daily_sales", 0) for d in daily_stats[pid][-30:])
            else:
                # 用评论数作为销量的代理指标
                total_sales = p.get("review_count", 0)
            sales_data.append({
                "product_id": pid,
                "title": p.get("title", "")[:40],
                "sales": total_sales,
            })

        # 按销量降序排列
        sales_data.sort(key=lambda x: x["sales"], reverse=True)
        total_sales = sum(d["sales"] for d in sales_data)

        if total_sales == 0:
            return {"available": False, "reason": "No sales data"}

        top1_sales = sales_data[0]["sales"] if len(sales_data) >= 1 else 0
        top3_sales = sum(d["sales"] for d in sales_data[:3])
        top10_sales = sum(d["sales"] for d in sales_data[:10])

        top1_ratio = top1_sales / total_sales
        top3_ratio = top3_sales / total_sales
        top10_ratio = top10_sales / total_sales

        # 垄断程度判定
        if top3_ratio > 0.7:
            level = "high_monopoly"
            description = "高度垄断，头部卖家占据绝大部分市场"
        elif top3_ratio > 0.5:
            level = "moderate_monopoly"
            description = "中度集中，头部有一定优势但仍有空间"
        elif top10_ratio > 0.5:
            level = "moderate_competition"
            description = "中度竞争，市场较为分散"
        else:
            level = "high_competition"
            description = "充分竞争，市场高度分散"

        return {
            "available": True,
            "top1_ratio": round(top1_ratio, 4),
            "top3_ratio": round(top3_ratio, 4),
            "top10_ratio": round(top10_ratio, 4),
            "monopoly_level": level,
            "description": description,
            "top3_products": sales_data[:3],
        }

    def _analyze_new_products(self, products: list[dict]) -> dict:
        """
        分析新品占比

        基于推算上架时间（最早评论日期）
        """
        now = datetime.now()
        three_months_ago = now - timedelta(days=90)
        one_year_ago = now - timedelta(days=365)

        total = len(products)
        new_3m = 0
        new_1y = 0

        for p in products:
            listed_date = p.get("estimated_listed_at", "")
            if not listed_date:
                continue
            try:
                dt = datetime.strptime(str(listed_date)[:10], "%Y-%m-%d")
                if dt >= three_months_ago:
                    new_3m += 1
                if dt >= one_year_ago:
                    new_1y += 1
            except (ValueError, TypeError):
                continue

        return {
            "total_products": total,
            "new_3m_count": new_3m,
            "new_3m_ratio": round(new_3m / max(total, 1), 4),
            "new_1y_count": new_1y,
            "new_1y_ratio": round(new_1y / max(total, 1), 4),
            "market_maturity": "emerging" if new_3m / max(total, 1) > 0.3 else (
                "growing" if new_1y / max(total, 1) > 0.5 else "mature"
            ),
        }

    def _analyze_price_distribution(self, products: list[dict]) -> dict:
        """分析价格分布"""
        prices = [p.get("price", 0) for p in products if p.get("price") and p["price"] > 0]
        if not prices:
            return {"available": False}

        prices.sort()
        n = len(prices)

        return {
            "available": True,
            "count": n,
            "min": round(min(prices), 0),
            "max": round(max(prices), 0),
            "avg": round(sum(prices) / n, 0),
            "median": round(prices[n // 2], 0),
            "p25": round(prices[n // 4], 0),
            "p75": round(prices[3 * n // 4], 0),
        }

    def _analyze_delivery_distribution(self, products: list[dict]) -> dict:
        """分析配送方式分布"""
        from collections import Counter
        delivery_counts = Counter(p.get("delivery_type", "unknown") for p in products)
        total = len(products)

        distribution = {}
        for dtype, count in delivery_counts.most_common():
            distribution[dtype] = {
                "count": count,
                "ratio": round(count / max(total, 1), 4),
            }

        return distribution

    def _ai_market_assessment(self, keyword: str, analysis_data: dict) -> dict:
        """AI 综合市场评估"""
        lang = get_language()
        output_lang = {"zh_CN": "Chinese", "en_US": "English", "ko_KR": "Korean"}.get(lang, "Chinese")

        prompt = f"""You are a Coupang cross-border e-commerce market analyst.

Keyword/Category: {keyword}
Product Count: {analysis_data.get('product_count', 0)}
GMV Estimate: {json.dumps(analysis_data.get('gmv_estimate', {}), ensure_ascii=False)}
Monopoly: {json.dumps(analysis_data.get('monopoly_analysis', {}), ensure_ascii=False)}
New Products: {json.dumps(analysis_data.get('new_product_analysis', {}), ensure_ascii=False)}
Price Distribution: {json.dumps(analysis_data.get('price_distribution', {}), ensure_ascii=False)}

Provide a JSON response with:
1. "market_summary": 2-3 sentence market overview
2. "opportunities": list of 3-5 market opportunities for new sellers
3. "risks": list of 3-5 market risks
4. "entry_strategy": recommended entry strategy
5. "recommended_price_range": suggested price range for new products
6. "overall_score": 1-10 market attractiveness score

Respond in {output_lang}. Return ONLY valid JSON."""

        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"AI market assessment error: {e}")
            return {}

    def _safe_avg(self, values: list) -> float:
        """安全计算平均值"""
        valid = [v for v in values if v and v > 0]
        return sum(valid) / len(valid) if valid else 0

    def close(self):
        self.client.close()
