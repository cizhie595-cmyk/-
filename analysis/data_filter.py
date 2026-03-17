"""
Coupang 选品系统 - 数据筛选与转化率计算模块
功能:
  1. 人工筛选 / AI自动筛选，过滤不相关产品
  2. 按30天重新计算点击量、销量、转化率
  3. 支持自定义筛选规则
"""

import json
from typing import Optional, Callable
from datetime import datetime, timedelta

from utils.logger import get_logger
from i18n import t

logger = get_logger()


# ============================================================
# 默认筛选规则配置
# ============================================================
DEFAULT_FILTER_RULES = {
    "min_review_count": 5,          # 最少评论数
    "min_rating": 2.0,              # 最低评分
    "min_30d_sales": 1,             # 最低30天销量
    "min_30d_clicks": 10,           # 最低30天点击量
    "min_conversion_rate": 0.001,   # 最低转化率 0.1%
    "max_conversion_rate": 0.80,    # 最高转化率 80%（过高可能刷单）
    "exclude_brands": [],           # 排除的品牌列表
    "exclude_delivery_types": [],   # 排除的配送方式
}


class DataFilter:
    """
    数据筛选器
    支持: 规则筛选 / AI智能筛选 / 手动审核
    """

    def __init__(self, rules: dict = None):
        self.rules = {**DEFAULT_FILTER_RULES, **(rules or {})}

    def filter_products(self, products: list[dict], daily_stats: dict = None) -> dict:
        """
        对产品列表进行筛选

        :param products: 产品列表
        :param daily_stats: 运营数据 {product_id: [daily_data]}
        :return: {"kept": [...], "filtered": [...], "summary": {...}}
        """
        logger.info(t("filter.start_filter"))

        kept = []
        filtered = []

        for product in products:
            product_id = product.get("coupang_product_id", "")

            # 计算30天汇总数据
            if daily_stats and product_id in daily_stats:
                summary_30d = self._calculate_30d_summary(daily_stats[product_id])
                product["summary_30d"] = summary_30d
            else:
                product["summary_30d"] = None

            # 执行筛选规则
            is_valid, reason = self._apply_rules(product)

            if is_valid:
                product["is_filtered"] = False
                product["filter_reason"] = None
                kept.append(product)
            else:
                product["is_filtered"] = True
                product["filter_reason"] = reason
                filtered.append(product)

        logger.info(t("filter.filtered_count", count=len(filtered)))
        logger.info(t("filter.remaining_count", count=len(kept)))

        return {
            "kept": kept,
            "filtered": filtered,
            "summary": {
                "total": len(products),
                "kept": len(kept),
                "filtered": len(filtered),
                "filter_rate": f"{len(filtered)/len(products)*100:.1f}%" if products else "0%",
            }
        }

    def _calculate_30d_summary(self, daily_data: list[dict]) -> dict:
        """
        计算30天汇总数据

        :param daily_data: 每日数据列表
        :return: 30天汇总
        """
        logger.debug(t("filter.calculating_30d"))

        # 只取最近30天的数据
        cutoff = datetime.now() - timedelta(days=30)
        recent_data = []
        for d in daily_data:
            try:
                date_str = str(d.get("record_date", ""))
                record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                if record_date >= cutoff:
                    recent_data.append(d)
            except (ValueError, TypeError):
                recent_data.append(d)  # 无法解析日期时保留

        total_clicks = sum(d.get("daily_clicks", 0) for d in recent_data)
        total_sales = sum(d.get("daily_sales", 0) for d in recent_data)
        total_views = sum(d.get("daily_views", 0) for d in recent_data)
        total_revenue = sum(d.get("daily_revenue", 0) for d in recent_data)

        # 转化率 = 销量 / 点击量
        conversion_rate = (total_sales / total_clicks) if total_clicks > 0 else 0

        return {
            "total_clicks_30d": total_clicks,
            "total_sales_30d": total_sales,
            "total_views_30d": total_views,
            "total_revenue_30d": total_revenue,
            "avg_conversion_rate": round(conversion_rate, 6),
            "data_days": len(recent_data),
            "avg_daily_sales": round(total_sales / max(len(recent_data), 1), 2),
            "avg_daily_clicks": round(total_clicks / max(len(recent_data), 1), 2),
        }

    def _apply_rules(self, product: dict) -> tuple[bool, str]:
        """
        应用筛选规则

        :return: (是否保留, 过滤原因)
        """
        reasons = []

        # 规则1: 评论数
        review_count = product.get("review_count", 0) or 0
        if review_count < self.rules["min_review_count"]:
            reasons.append(f"评论数不足({review_count}<{self.rules['min_review_count']})")

        # 规则2: 评分
        rating = product.get("rating") or 0
        if rating > 0 and rating < self.rules["min_rating"]:
            reasons.append(f"评分过低({rating}<{self.rules['min_rating']})")

        # 规则3: 品牌排除
        brand = product.get("brand_name", "")
        if brand and brand in self.rules["exclude_brands"]:
            reasons.append(f"排除品牌({brand})")

        # 规则4: 配送方式排除
        delivery = product.get("delivery_type", "")
        if delivery and delivery in self.rules["exclude_delivery_types"]:
            reasons.append(f"排除配送方式({delivery})")

        # 规则5: 30天数据筛选
        summary = product.get("summary_30d")
        if summary:
            if summary["total_sales_30d"] < self.rules["min_30d_sales"]:
                reasons.append(f"30天销量不足({summary['total_sales_30d']}<{self.rules['min_30d_sales']})")

            if summary["total_clicks_30d"] < self.rules["min_30d_clicks"]:
                reasons.append(f"30天点击量不足({summary['total_clicks_30d']}<{self.rules['min_30d_clicks']})")

            cr = summary["avg_conversion_rate"]
            if cr > 0 and cr < self.rules["min_conversion_rate"]:
                reasons.append(f"转化率过低({cr:.4f}<{self.rules['min_conversion_rate']})")

            if cr > self.rules["max_conversion_rate"]:
                reasons.append(f"转化率异常高({cr:.4f}>{self.rules['max_conversion_rate']}), 疑似刷单")

        if reasons:
            return False, "; ".join(reasons)

        return True, ""

    def ai_filter(self, products: list[dict], keyword: str, ai_client=None) -> list[dict]:
        """
        使用AI进行智能筛选（判断产品与关键词的相关性）

        :param products: 产品列表
        :param keyword: 搜索关键词
        :param ai_client: OpenAI客户端实例
        :return: 筛选后的产品列表
        """
        logger.info(t("filter.ai_filter_start"))

        if not ai_client:
            logger.warning("AI client not configured, skipping AI filter")
            return products

        # 构建批量判断的prompt
        product_titles = [
            f"{i+1}. {p.get('title', '')}"
            for i, p in enumerate(products)
        ]
        titles_text = "\n".join(product_titles)

        prompt = f"""You are a product relevance analyst for Coupang (Korean e-commerce).

Search keyword: "{keyword}"

Product list:
{titles_text}

For each product, determine if it is relevant to the search keyword.
Return a JSON array of objects: [{{"index": 1, "relevant": true/false, "reason": "brief reason"}}]

Only mark as irrelevant if the product is clearly unrelated to the keyword.
Respond ONLY with the JSON array, no other text."""

        try:
            response = ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            result_text = response.choices[0].message.content.strip()

            # 解析JSON结果
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            results = json.loads(result_text)

            # 标记不相关产品
            for r in results:
                idx = r.get("index", 0) - 1
                if 0 <= idx < len(products) and not r.get("relevant", True):
                    products[idx]["is_filtered"] = True
                    products[idx]["filter_reason"] = f"AI判定不相关: {r.get('reason', '')}"

        except Exception as e:
            logger.error(f"AI filter error: {e}")

        return products

    def manual_review(self, products: list[dict]) -> list[dict]:
        """
        手动审核筛选结果（交互式命令行）

        :param products: 待审核的产品列表
        :return: 审核后的产品列表
        """
        print(f"\n{t('filter.manual_filter_prompt')}")
        print(f"{'='*60}")

        for i, p in enumerate(products):
            status = "✗ FILTERED" if p.get("is_filtered") else "✓ KEPT"
            reason = p.get("filter_reason", "")
            print(f"\n[{i+1}] {status}")
            print(f"    {p.get('title', '')[:60]}")
            print(f"    Price: {p.get('price', 'N/A')} | Rating: {p.get('rating', 'N/A')} | Reviews: {p.get('review_count', 0)}")
            if reason:
                print(f"    Reason: {reason}")

            if p.get("is_filtered"):
                choice = input(f"    Keep this product? (y/N): ").strip().lower()
                if choice == "y":
                    p["is_filtered"] = False
                    p["filter_reason"] = None
            else:
                choice = input(f"    Filter out? (y/N): ").strip().lower()
                if choice == "y":
                    p["is_filtered"] = True
                    p["filter_reason"] = "手动过滤"

        return products
