"""
Amazon 数据清洗与精准筛选模块

针对 Amazon 平台的数据特征进行适配：
  - 支持 BSR 排名筛选
  - 支持 FBA/FBM 物流方式筛选
  - 支持价格区间筛选（多币种）
  - AI 自动识别不相关产品
  - 按 30 天周期重算预估点击量、销量、转化率
"""

import json
from typing import Optional
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger()


# ============================================================
# Amazon 默认筛选规则
# ============================================================
AMAZON_DEFAULT_RULES = {
    # 基础筛选
    "min_review_count": 10,             # 最少评论数
    "max_review_count": None,           # 最多评论数（None=不限）
    "min_rating": 3.0,                  # 最低评分
    "min_price": None,                  # 最低价格（美元）
    "max_price": None,                  # 最高价格（美元）

    # BSR 筛选
    "max_bsr": None,                    # 最高 BSR 排名（None=不限）
    "min_bsr": None,                    # 最低 BSR 排名

    # 物流筛选
    "fulfillment_filter": "all",        # all / fba_only / fbm_only
    "require_prime": False,             # 是否要求 Prime

    # 竞争度筛选
    "max_seller_count": None,           # 最大卖家数量
    "min_monthly_sales": None,          # 最低月销量

    # 品牌筛选
    "exclude_brands": [],               # 排除品牌列表
    "exclude_amazon_brands": True,      # 排除亚马逊自营品牌

    # 转化率筛选
    "min_conversion_rate": 0.005,       # 最低转化率 0.5%
    "max_conversion_rate": 0.80,        # 最高转化率 80%（异常高可能刷单）

    # 上架时间筛选
    "max_listing_age_days": None,       # 最大上架天数
    "min_listing_age_days": None,       # 最小上架天数

    # 广告筛选
    "exclude_sponsored": True,          # 排除赞助（广告）产品
}

# 亚马逊自营/关联品牌列表
AMAZON_OWNED_BRANDS = {
    "Amazon Basics", "AmazonBasics", "Amazon Essentials",
    "Amazon Commercial", "Solimo", "Presto!", "Mama Bear",
    "Happy Belly", "Wickedly Prime", "Amazon Elements",
    "Pinzon", "Stone & Beam", "Rivet", "Ravenna Home",
}


class AmazonDataFilter:
    """
    Amazon 专用数据筛选器

    从海量初步数据中剔除无效干扰项，锁定高潜力竞品。
    支持: 规则筛选 / AI 智能筛选 / 手动审核。
    """

    def __init__(self, rules: dict = None):
        self.rules = {**AMAZON_DEFAULT_RULES, **(rules or {})}

    def filter_products(self, products: list[dict],
                        backend_data: dict = None) -> dict:
        """
        对 Amazon 产品列表进行多维度筛选。

        :param products: 产品列表（来自搜索爬虫或 SP-API）
        :param backend_data: 后台业务报告数据 {asin: {...}}
        :return: {"kept": [...], "filtered": [...], "summary": {...}}
        """
        logger.info(f"[Amazon筛选] 开始筛选 {len(products)} 个产品")

        kept = []
        filtered = []
        filter_reasons_stats = {}

        for product in products:
            asin = product.get("asin", "")

            # 合并后台数据
            if backend_data and asin in backend_data:
                product["backend_metrics"] = backend_data[asin]
                self._enrich_with_backend(product, backend_data[asin])

            # 执行筛选规则
            is_valid, reasons = self._apply_amazon_rules(product)

            if is_valid:
                product["is_filtered"] = False
                product["filter_reasons"] = []
                kept.append(product)
            else:
                product["is_filtered"] = True
                product["filter_reasons"] = reasons
                filtered.append(product)
                # 统计过滤原因
                for reason in reasons:
                    category = reason.split("(")[0].strip()
                    filter_reasons_stats[category] = filter_reasons_stats.get(category, 0) + 1

        # 对保留的产品按综合评分排序
        kept = self._rank_products(kept)

        summary = {
            "total": len(products),
            "kept": len(kept),
            "filtered": len(filtered),
            "filter_rate": f"{len(filtered)/len(products)*100:.1f}%" if products else "0%",
            "filter_reasons_breakdown": filter_reasons_stats,
        }

        logger.info(f"[Amazon筛选] 筛选完成: 保留 {len(kept)} / 过滤 {len(filtered)} | 过滤率: {summary['filter_rate']}")
        return {"kept": kept, "filtered": filtered, "summary": summary}

    def _apply_amazon_rules(self, product: dict) -> tuple[bool, list[str]]:
        """
        应用 Amazon 专用筛选规则。

        :return: (是否保留, 过滤原因列表)
        """
        reasons = []

        # 1. 评论数筛选
        review_count = product.get("review_count", 0) or 0
        if review_count < self.rules["min_review_count"]:
            reasons.append(f"评论数不足({review_count} < {self.rules['min_review_count']})")
        if self.rules["max_review_count"] and review_count > self.rules["max_review_count"]:
            reasons.append(f"评论数过多({review_count} > {self.rules['max_review_count']})")

        # 2. 评分筛选
        rating = product.get("rating", 0) or 0
        if rating > 0 and rating < self.rules["min_rating"]:
            reasons.append(f"评分过低({rating} < {self.rules['min_rating']})")

        # 3. 价格区间筛选
        price = product.get("price")
        if price is not None:
            if self.rules["min_price"] and price < self.rules["min_price"]:
                reasons.append(f"价格过低(${price} < ${self.rules['min_price']})")
            if self.rules["max_price"] and price > self.rules["max_price"]:
                reasons.append(f"价格过高(${price} > ${self.rules['max_price']})")

        # 4. BSR 排名筛选
        bsr = product.get("bsr", 0) or 0
        if bsr > 0:
            if self.rules["max_bsr"] and bsr > self.rules["max_bsr"]:
                reasons.append(f"BSR排名过高(#{bsr} > #{self.rules['max_bsr']})")
            if self.rules["min_bsr"] and bsr < self.rules["min_bsr"]:
                reasons.append(f"BSR排名过低(#{bsr} < #{self.rules['min_bsr']})")

        # 5. 物流方式筛选
        fulfillment = product.get("fulfillment", {})
        fulfillment_type = fulfillment.get("type", "") if isinstance(fulfillment, dict) else str(fulfillment)
        if self.rules["fulfillment_filter"] == "fba_only" and fulfillment_type != "FBA":
            reasons.append(f"非FBA发货({fulfillment_type})")
        elif self.rules["fulfillment_filter"] == "fbm_only" and fulfillment_type != "FBM":
            reasons.append(f"非FBM发货({fulfillment_type})")

        # 6. Prime 筛选
        if self.rules["require_prime"]:
            is_prime = product.get("is_prime", False)
            if isinstance(fulfillment, dict):
                is_prime = is_prime or fulfillment.get("is_prime", False)
            if not is_prime:
                reasons.append("非Prime商品")

        # 7. 品牌排除
        brand = product.get("brand", "")
        if brand and brand in self.rules["exclude_brands"]:
            reasons.append(f"排除品牌({brand})")
        if self.rules["exclude_amazon_brands"] and brand in AMAZON_OWNED_BRANDS:
            reasons.append(f"亚马逊自营品牌({brand})")

        # 8. 广告产品排除
        if self.rules["exclude_sponsored"] and product.get("is_sponsored"):
            reasons.append("赞助/广告产品")

        # 9. 月销量筛选（如果有 Keepa 数据）
        monthly_sales = product.get("estimated_monthly_sales", 0)
        if self.rules["min_monthly_sales"] and monthly_sales > 0:
            if monthly_sales < self.rules["min_monthly_sales"]:
                reasons.append(f"月销量不足({monthly_sales} < {self.rules['min_monthly_sales']})")

        # 10. 转化率筛选（如果有后台数据）
        cr = product.get("conversion_rate", 0)
        if cr > 0:
            if cr < self.rules["min_conversion_rate"]:
                reasons.append(f"转化率过低({cr:.2%} < {self.rules['min_conversion_rate']:.2%})")
            if cr > self.rules["max_conversion_rate"]:
                reasons.append(f"转化率异常高({cr:.2%} > {self.rules['max_conversion_rate']:.2%}), 疑似刷单")

        if reasons:
            return False, reasons
        return True, []

    def _enrich_with_backend(self, product: dict, backend: dict):
        """用后台数据补充产品信息"""
        product["sessions"] = backend.get("sessions", 0)
        product["page_views"] = backend.get("page_views", 0)
        product["conversion_rate"] = backend.get("conversion_rate", 0)
        product["units_ordered"] = backend.get("units_ordered", 0)
        product["buy_box_pct"] = backend.get("buy_box_pct", 0)
        product["ordered_sales"] = backend.get("ordered_sales", 0)

    def _rank_products(self, products: list[dict]) -> list[dict]:
        """
        对保留的产品进行综合评分排序。

        评分维度:
          - 销量/BSR 权重 40%
          - 评分权重 20%
          - 评论数权重 20%
          - 价格竞争力 20%
        """
        if not products:
            return products

        # 归一化各维度
        max_reviews = max((p.get("review_count", 0) for p in products), default=1) or 1
        max_rating = 5.0
        bsr_values = [p.get("bsr", 0) for p in products if p.get("bsr", 0) > 0]
        max_bsr = max(bsr_values) if bsr_values else 1

        for product in products:
            score = 0

            # BSR 评分（排名越低越好，反向归一化）
            bsr = product.get("bsr", 0)
            if bsr > 0 and max_bsr > 0:
                score += (1 - bsr / max_bsr) * 40
            else:
                score += 20  # 无 BSR 数据给中间分

            # 评分
            rating = product.get("rating", 0) or 0
            score += (rating / max_rating) * 20

            # 评论数（对数归一化）
            import math
            review_count = product.get("review_count", 0) or 0
            if review_count > 0 and max_reviews > 0:
                score += (math.log(review_count + 1) / math.log(max_reviews + 1)) * 20

            # 价格竞争力（中间价位得分最高）
            price = product.get("price")
            if price and price > 0:
                prices = [p.get("price", 0) for p in products if p.get("price")]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    price_ratio = abs(price - avg_price) / avg_price if avg_price > 0 else 0
                    score += max(0, (1 - price_ratio)) * 20

            product["competition_score"] = round(score, 2)

        # 按综合评分降序排列
        products.sort(key=lambda x: x.get("competition_score", 0), reverse=True)
        return products

    def ai_filter(self, products: list[dict], keyword: str,
                  ai_client=None, model: str = "gpt-4.1-mini") -> list[dict]:
        """
        使用 AI 进行智能筛选（判断产品与关键词的相关性）。

        :param products: 产品列表
        :param keyword: 搜索关键词
        :param ai_client: OpenAI 客户端实例
        :param model: 使用的模型名称
        :return: 标记后的产品列表
        """
        if not ai_client:
            logger.warning("[Amazon筛选] AI 客户端未配置，跳过 AI 筛选")
            return products

        logger.info(f"[Amazon筛选] 开始 AI 智能筛选 | 关键词: {keyword} | 产品数: {len(products)}")

        # 分批处理（每批最多30个）
        batch_size = 30
        for start in range(0, len(products), batch_size):
            batch = products[start:start + batch_size]
            product_lines = [
                f"{i+1}. [{p.get('asin', '')}] {p.get('title', '')[:80]} | ${p.get('price', 'N/A')} | {p.get('rating', 0)}★ | {p.get('review_count', 0)} reviews"
                for i, p in enumerate(batch)
            ]
            titles_text = "\n".join(product_lines)

            prompt = f"""You are an Amazon product relevance analyst.

Search keyword: "{keyword}"

Product list:
{titles_text}

For each product, determine:
1. Is it relevant to the search keyword?
2. Is it a viable competitive product worth analyzing?

Return a JSON array: [{{"index": 1, "relevant": true/false, "reason": "brief reason"}}]

Mark as irrelevant if:
- Product is clearly unrelated to the keyword
- Product is an accessory/addon rather than the main product
- Product is a bundle/multi-pack that distorts price comparison

Respond ONLY with the JSON array."""

            try:
                response = ai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                result_text = response.choices[0].message.content.strip()

                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]

                results = json.loads(result_text)

                for r in results:
                    idx = r.get("index", 0) - 1
                    if 0 <= idx < len(batch) and not r.get("relevant", True):
                        actual_idx = start + idx
                        products[actual_idx]["is_filtered"] = True
                        products[actual_idx]["filter_reasons"] = [
                            f"AI判定不相关: {r.get('reason', '')}"
                        ]

            except Exception as e:
                logger.error(f"[Amazon筛选] AI 筛选异常: {e}")

        filtered_count = sum(1 for p in products if p.get("is_filtered"))
        logger.info(f"[Amazon筛选] AI 筛选完成: {filtered_count} 个产品被标记为不相关")
        return products

    def recalculate_30d_metrics(self, products: list[dict],
                                keepa_data: dict = None,
                                backend_data: dict = None) -> list[dict]:
        """
        按 PRD 3.2.2 核心指标重算公式，对所有产品进行 30 天归一化计算。

        归一化指标：
          - Sales_30D:   30天预估销量（Keepa > BSR反推 > 后台数据）
          - Revenue_30D: 30天预估营收 = Sales_30D * Avg_Price_30D
          - Clicks_30D:  30天预估点击量（后台 sessions 或 BSR 反推）
          - CVR_30D:     30天转化率 = Sales_30D / Clicks_30D
          - BSR_Avg_30D: 30天平均BSR
          - Price_Avg_30D: 30天平均价格
          - Review_Velocity: 月均评论增速
          - Normalized_Score: 归一化综合评分 (0-100)

        :param products: 产品列表
        :param keepa_data: Keepa 历史数据 {asin: {...}}
        :param backend_data: 后台业务报告数据 {asin: {...}}
        :return: 补充了 metrics_30d 的产品列表
        """
        import math

        for product in products:
            asin = product.get("asin", "")
            metrics = {"period": "30d", "data_sources": []}

            # ── 1. Sales_30D 销量归一化 ──
            sales_30d = 0
            if keepa_data and asin in keepa_data:
                kd = keepa_data[asin]
                sales_30d = kd.get("estimated_monthly_sales", 0)
                metrics["avg_price_30d"] = kd.get("avg_price", product.get("price"))
                metrics["bsr_avg_30d"] = kd.get("avg_bsr")
                metrics["data_sources"].append("keepa")

                # 评论增速 (Keepa review_count_history)
                review_history = kd.get("review_count_history", [])
                if len(review_history) >= 2:
                    first_rc = review_history[0].get("value", 0)
                    last_rc = review_history[-1].get("value", 0)
                    days_span = max(1, (review_history[-1].get("timestamp", 0) - review_history[0].get("timestamp", 0)) / 86400)
                    metrics["review_velocity"] = round((last_rc - first_rc) / (days_span / 30), 1)
            else:
                metrics["avg_price_30d"] = product.get("price")
                metrics["bsr_avg_30d"] = product.get("bsr")

            # BSR 反推销量（当 Keepa 数据不可用时）
            if sales_30d <= 0:
                bsr = product.get("bsr", 0)
                if bsr > 0:
                    sales_30d = self._estimate_sales_from_bsr(
                        bsr, product.get("category", "general")
                    )
                    metrics["data_sources"].append("bsr_estimate")

            # 后台数据补充
            if backend_data and asin in backend_data:
                bd = backend_data[asin]
                if bd.get("units_ordered", 0) > 0:
                    sales_30d = max(sales_30d, bd["units_ordered"])
                    metrics["data_sources"].append("backend")

            metrics["sales_30d"] = sales_30d

            # ── 2. Revenue_30D 营收归一化 ──
            avg_price = metrics.get("avg_price_30d") or product.get("price", 0) or 0
            metrics["revenue_30d"] = round(sales_30d * avg_price, 2)

            # ── 3. Clicks_30D 点击量归一化 ──
            clicks_30d = 0
            if backend_data and asin in backend_data:
                clicks_30d = backend_data[asin].get("sessions", 0)
            elif sales_30d > 0:
                # 无后台数据时，基于行业平均转化率 (10-15%) 反推
                estimated_cvr = 0.12  # 行业平均
                clicks_30d = int(sales_30d / estimated_cvr)
            metrics["clicks_30d"] = clicks_30d

            # ── 4. CVR_30D 转化率归一化 ──
            if clicks_30d > 0 and sales_30d > 0:
                metrics["cvr_30d"] = round(sales_30d / clicks_30d, 4)
            elif backend_data and asin in backend_data:
                metrics["cvr_30d"] = backend_data[asin].get("conversion_rate", 0)
            elif product.get("conversion_rate"):
                metrics["cvr_30d"] = product["conversion_rate"]
            else:
                metrics["cvr_30d"] = 0

            # ── 5. Review Velocity 评论增速 ──
            if "review_velocity" not in metrics:
                review_count = product.get("review_count", 0)
                listed_since = product.get("listed_since", "")
                if review_count > 0 and listed_since:
                    try:
                        from datetime import datetime
                        listed_date = datetime.strptime(listed_since[:10], "%Y-%m-%d")
                        months_active = max(1, (datetime.now() - listed_date).days / 30)
                        metrics["review_velocity"] = round(review_count / months_active, 1)
                    except (ValueError, TypeError):
                        metrics["review_velocity"] = 0
                else:
                    metrics["review_velocity"] = 0

            product["metrics_30d"] = metrics

        # ── 6. Normalized_Score 归一化综合评分 (0-100) ──
        self._normalize_scores(products)

        return products

    def _normalize_scores(self, products: list[dict]):
        """
        PRD 3.2.2 归一化综合评分。

        各维度权重：
          - Sales_30D:      30%
          - Revenue_30D:    20%
          - CVR_30D:        15%
          - Rating:         15%
          - Review_Velocity: 10%
          - BSR (反向):      10%

        所有维度先 Min-Max 归一化到 [0, 1]，再加权求和得到 0-100 分。
        """
        import math

        if not products:
            return

        # 收集各维度的值
        def safe_get(p, *keys):
            val = p
            for k in keys:
                if isinstance(val, dict):
                    val = val.get(k, 0)
                else:
                    return 0
            return val or 0

        sales_vals = [safe_get(p, "metrics_30d", "sales_30d") for p in products]
        revenue_vals = [safe_get(p, "metrics_30d", "revenue_30d") for p in products]
        cvr_vals = [safe_get(p, "metrics_30d", "cvr_30d") for p in products]
        rating_vals = [p.get("rating", 0) or 0 for p in products]
        rv_vals = [safe_get(p, "metrics_30d", "review_velocity") for p in products]
        bsr_vals = [p.get("bsr", 0) or 0 for p in products]

        def min_max(vals):
            """Min-Max 归一化"""
            mn, mx = min(vals) if vals else 0, max(vals) if vals else 0
            rng = mx - mn
            if rng == 0:
                return [0.5] * len(vals)
            return [(v - mn) / rng for v in vals]

        def min_max_inverse(vals):
            """反向 Min-Max 归一化（BSR 越小越好）"""
            mn, mx = min(vals) if vals else 0, max(vals) if vals else 0
            rng = mx - mn
            if rng == 0:
                return [0.5] * len(vals)
            return [1 - (v - mn) / rng for v in vals]

        norm_sales = min_max(sales_vals)
        norm_revenue = min_max(revenue_vals)
        norm_cvr = min_max(cvr_vals)
        norm_rating = min_max(rating_vals)
        norm_rv = min_max(rv_vals)
        norm_bsr = min_max_inverse(bsr_vals)

        # 加权求和
        weights = {
            "sales": 0.30,
            "revenue": 0.20,
            "cvr": 0.15,
            "rating": 0.15,
            "review_velocity": 0.10,
            "bsr": 0.10,
        }

        for i, product in enumerate(products):
            score = (
                norm_sales[i] * weights["sales"] +
                norm_revenue[i] * weights["revenue"] +
                norm_cvr[i] * weights["cvr"] +
                norm_rating[i] * weights["rating"] +
                norm_rv[i] * weights["review_velocity"] +
                norm_bsr[i] * weights["bsr"]
            ) * 100

            product["metrics_30d"]["normalized_score"] = round(score, 1)
            product["metrics_30d"]["score_breakdown"] = {
                "sales": round(norm_sales[i] * 100, 1),
                "revenue": round(norm_revenue[i] * 100, 1),
                "cvr": round(norm_cvr[i] * 100, 1),
                "rating": round(norm_rating[i] * 100, 1),
                "review_velocity": round(norm_rv[i] * 100, 1),
                "bsr": round(norm_bsr[i] * 100, 1),
            }

    @staticmethod
    def _estimate_sales_from_bsr(bsr: int, category: str = "general") -> int:
        """
        基于 BSR 排名预估月销量。

        使用经验公式（不同类目系数不同）:
        estimated_sales = base * (bsr ^ -exponent)

        这是一个近似值，精确数据需要 Keepa/Jungle Scout 等工具。
        """
        # 通用类目的经验参数
        category_params = {
            "general": {"base": 120000, "exponent": 0.75},
            "electronics": {"base": 150000, "exponent": 0.78},
            "home_kitchen": {"base": 100000, "exponent": 0.72},
            "clothing": {"base": 80000, "exponent": 0.70},
            "toys": {"base": 90000, "exponent": 0.73},
        }

        params = category_params.get(category, category_params["general"])
        base = params["base"]
        exp = params["exponent"]

        if bsr <= 0:
            return 0

        estimated = base * (bsr ** -exp)
        return max(1, int(estimated))
