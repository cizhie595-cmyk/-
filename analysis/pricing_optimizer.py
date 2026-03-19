"""
定价策略优化器 (Pricing Optimizer)

Step 9 扩展模块 - 最优定价建议、价格弹性分析、多策略对比

功能:
1. 竞品价格分布分析（价格带识别、价格密度图数据）
2. 最优定价建议（基于成本、竞争和利润目标）
3. 价格弹性模拟（不同价格下的预期销量和利润）
4. 多定价策略对比（渗透定价、撇脂定价、竞争定价等）
5. 促销定价建议（Coupon、Lightning Deal 等）
"""

import math
from datetime import datetime
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class PricingOptimizer:
    """
    Amazon 定价策略优化器

    基于竞品价格分布、成本结构和市场数据，
    提供最优定价建议和多策略对比分析。
    """

    # Amazon 费用参数（简化版，详细费用由 AmazonFBAProfitCalculator 计算）
    DEFAULT_FEE_RATES = {
        "referral_fee_pct": 0.15,     # 佣金率 15%
        "fba_fee_estimate": 5.50,     # FBA 费用估算（美元）
        "ppc_acos_target": 0.25,      # PPC ACOS 目标 25%
        "return_rate": 0.03,          # 退货率 3%
    }

    # 定价策略定义
    STRATEGIES = {
        "penetration": {
            "name": "渗透定价",
            "description": "低于市场均价 15-25%，快速获取市场份额和评论",
            "price_factor_range": (0.75, 0.85),
            "suitable_for": "新品上架期、评论数 < 50",
            "risk": "利润薄，需要足够资金支撑",
        },
        "competitive": {
            "name": "竞争定价",
            "description": "与市场均价持平或略低 5-10%",
            "price_factor_range": (0.90, 1.00),
            "suitable_for": "中期稳定增长、评论数 50-200",
            "risk": "需要差异化卖点支撑",
        },
        "value": {
            "name": "价值定价",
            "description": "高于市场均价 5-15%，强调产品价值和品质",
            "price_factor_range": (1.05, 1.15),
            "suitable_for": "有明确差异化优势、评论数 > 200 且评分 > 4.3",
            "risk": "需要优质 Listing 和品牌背书",
        },
        "premium": {
            "name": "高端定价",
            "description": "高于市场均价 20-40%，定位高端市场",
            "price_factor_range": (1.20, 1.40),
            "suitable_for": "品牌产品、独特设计、专利技术",
            "risk": "市场容量有限，需要强品牌力",
        },
        "skimming": {
            "name": "撇脂定价",
            "description": "初期高价后逐步降价，适合创新产品",
            "price_factor_range": (1.30, 1.50),
            "suitable_for": "市场首创产品、无直接竞品",
            "risk": "可能吸引竞争者快速跟进",
        },
    }

    def __init__(self, marketplace: str = "US", exchange_rate: float = 7.25):
        """
        :param marketplace: 市场站点
        :param exchange_rate: 汇率（人民币/美元）
        """
        self.marketplace = marketplace
        self.exchange_rate = exchange_rate

    # ================================================================
    # 竞品价格分布分析
    # ================================================================

    def analyze_price_distribution(self, products: list[dict]) -> dict:
        """
        分析竞品价格分布

        :param products: 竞品产品列表
        :return: 价格分布分析结果
        """
        prices = []
        for p in products:
            price = p.get("price") or p.get("price_current") or 0
            if price and float(price) > 0:
                prices.append(float(price))

        if not prices:
            return {"error": "No valid price data"}

        prices.sort()
        n = len(prices)

        # 基础统计
        avg_price = sum(prices) / n
        median_price = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        std_dev = math.sqrt(sum((p - avg_price) ** 2 for p in prices) / n)

        # 四分位数
        q1 = prices[n // 4]
        q3 = prices[3 * n // 4]
        iqr = q3 - q1

        # 价格带识别（按价格区间分组）
        price_range = max(prices) - min(prices)
        num_bands = min(max(3, n // 5), 8)
        band_width = price_range / num_bands if num_bands > 0 else price_range

        bands = []
        for i in range(num_bands):
            band_min = min(prices) + i * band_width
            band_max = band_min + band_width
            band_products = [p for p in prices if band_min <= p < band_max or (i == num_bands - 1 and p == max(prices))]
            if band_products:
                bands.append({
                    "range": f"${band_min:.2f} - ${band_max:.2f}",
                    "min": round(band_min, 2),
                    "max": round(band_max, 2),
                    "count": len(band_products),
                    "percentage": round(len(band_products) / n * 100, 1),
                    "avg_price": round(sum(band_products) / len(band_products), 2),
                })

        # 找出价格密集区（最多产品的价格带）
        densest_band = max(bands, key=lambda b: b["count"]) if bands else None

        # 找出价格空白区（产品少的价格带）
        gap_bands = [b for b in bands if b["count"] <= max(1, n * 0.1)]

        return {
            "total_products": n,
            "statistics": {
                "min": round(min(prices), 2),
                "max": round(max(prices), 2),
                "avg": round(avg_price, 2),
                "median": round(median_price, 2),
                "std_dev": round(std_dev, 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(iqr, 2),
            },
            "price_bands": bands,
            "densest_band": densest_band,
            "gap_bands": gap_bands,
            "chart_data": {
                "labels": [b["range"] for b in bands],
                "values": [b["count"] for b in bands],
                "prices": prices,
            },
        }

    # ================================================================
    # 最优定价建议
    # ================================================================

    def suggest_optimal_price(self, cost_params: dict,
                               products: list[dict],
                               target_margin: float = 0.25) -> dict:
        """
        计算最优定价建议

        :param cost_params: 成本参数
            - sourcing_cost_rmb: 采购成本（人民币）
            - shipping_cost_per_kg: 头程运费（人民币/kg）
            - weight_kg: 产品重量
            - fba_fee: FBA 费用（美元，可选）
        :param products: 竞品产品列表
        :param target_margin: 目标利润率（默认 25%）
        :return: 定价建议
        """
        # 计算成本
        sourcing_rmb = cost_params.get("sourcing_cost_rmb", 0)
        shipping_rmb = cost_params.get("shipping_cost_per_kg", 0) * cost_params.get("weight_kg", 0.5)
        total_cost_rmb = sourcing_rmb + shipping_rmb
        total_cost_usd = total_cost_rmb / self.exchange_rate

        # Amazon 费用
        fba_fee = cost_params.get("fba_fee", self.DEFAULT_FEE_RATES["fba_fee_estimate"])
        referral_pct = cost_params.get("referral_fee_pct", self.DEFAULT_FEE_RATES["referral_fee_pct"])

        # 分析竞品价格
        distribution = self.analyze_price_distribution(products)
        market_avg = distribution.get("statistics", {}).get("avg", 0)
        market_median = distribution.get("statistics", {}).get("median", 0)

        # 计算盈亏平衡价格: price = (cost + fba_fee) / (1 - referral_pct - return_rate)
        return_rate = self.DEFAULT_FEE_RATES["return_rate"]
        breakeven_price = (total_cost_usd + fba_fee) / (1 - referral_pct - return_rate)

        # 目标利润价格: price = (cost + fba_fee) / (1 - referral_pct - return_rate - target_margin)
        target_price = (total_cost_usd + fba_fee) / (1 - referral_pct - return_rate - target_margin)

        # 最优价格建议（综合成本和市场）
        if market_avg > 0:
            # 如果目标价格低于市场均价，有竞争力
            if target_price <= market_avg * 0.95:
                optimal_price = target_price
                strategy = "competitive"
                rationale = "目标利润价格低于市场均价，具有价格竞争力"
            elif target_price <= market_avg * 1.05:
                optimal_price = market_avg * 0.95  # 略低于市场均价
                strategy = "competitive"
                rationale = "目标利润价格接近市场均价，建议略低定价争取转化率"
            elif target_price <= market_avg * 1.20:
                optimal_price = target_price
                strategy = "value"
                rationale = "成本较高，需要价值定价策略，强调产品差异化"
            else:
                optimal_price = target_price
                strategy = "premium"
                rationale = "成本结构决定了必须高端定价，需要强品牌支撑"
        else:
            optimal_price = target_price
            strategy = "competitive"
            rationale = "无竞品价格数据，基于成本加成定价"

        # 计算最优价格下的利润
        referral_fee = optimal_price * referral_pct
        return_cost = optimal_price * return_rate
        profit = optimal_price - total_cost_usd - fba_fee - referral_fee - return_cost
        margin = profit / optimal_price * 100 if optimal_price > 0 else 0

        # 建议价格区间
        price_floor = max(breakeven_price * 1.05, optimal_price * 0.85)  # 最低不低于盈亏平衡 + 5%
        price_ceiling = optimal_price * 1.20

        return {
            "optimal_price": round(optimal_price, 2),
            "price_floor": round(price_floor, 2),
            "price_ceiling": round(price_ceiling, 2),
            "breakeven_price": round(breakeven_price, 2),
            "target_margin_price": round(target_price, 2),
            "recommended_strategy": strategy,
            "strategy_name": self.STRATEGIES.get(strategy, {}).get("name", strategy),
            "rationale": rationale,
            "cost_breakdown": {
                "sourcing_cost_usd": round(sourcing_rmb / self.exchange_rate, 2),
                "shipping_cost_usd": round(shipping_rmb / self.exchange_rate, 2),
                "total_landed_cost_usd": round(total_cost_usd, 2),
                "fba_fee": round(fba_fee, 2),
                "referral_fee": round(referral_fee, 2),
                "return_cost": round(return_cost, 2),
            },
            "profit_at_optimal": {
                "profit_per_unit": round(profit, 2),
                "margin_pct": round(margin, 1),
            },
            "market_context": {
                "market_avg_price": round(market_avg, 2),
                "market_median_price": round(market_median, 2),
                "price_vs_market": f"{((optimal_price / market_avg - 1) * 100):+.1f}%" if market_avg > 0 else "N/A",
            },
        }

    # ================================================================
    # 价格弹性模拟
    # ================================================================

    def simulate_price_elasticity(self, cost_params: dict,
                                    products: list[dict],
                                    price_range: tuple = None,
                                    steps: int = 10) -> dict:
        """
        模拟不同价格下的预期销量和利润

        使用简化的价格弹性模型:
        - 价格低于市场均价 → 销量增加（弹性系数 -1.5 到 -2.5）
        - 价格高于市场均价 → 销量减少

        :param cost_params: 成本参数
        :param products: 竞品产品列表
        :param price_range: 价格范围 (min, max)，默认自动计算
        :param steps: 模拟步数
        :return: 弹性模拟结果
        """
        # 计算成本
        sourcing_rmb = cost_params.get("sourcing_cost_rmb", 0)
        shipping_rmb = cost_params.get("shipping_cost_per_kg", 0) * cost_params.get("weight_kg", 0.5)
        total_cost_usd = (sourcing_rmb + shipping_rmb) / self.exchange_rate
        fba_fee = cost_params.get("fba_fee", self.DEFAULT_FEE_RATES["fba_fee_estimate"])
        referral_pct = self.DEFAULT_FEE_RATES["referral_fee_pct"]
        return_rate = self.DEFAULT_FEE_RATES["return_rate"]

        # 市场数据
        distribution = self.analyze_price_distribution(products)
        market_avg = distribution.get("statistics", {}).get("avg", 0)

        if not market_avg:
            return {"error": "No market price data available"}

        # 估算基准月销量（从竞品数据推算）
        base_monthly_sales = self._estimate_base_sales(products)

        # 价格范围
        if not price_range:
            breakeven = (total_cost_usd + fba_fee) / (1 - referral_pct - return_rate)
            price_min = max(breakeven * 0.95, market_avg * 0.60)
            price_max = market_avg * 1.50
        else:
            price_min, price_max = price_range

        step_size = (price_max - price_min) / steps

        # 价格弹性系数（Amazon 典型值 -1.5 到 -2.5）
        elasticity = -2.0

        simulations = []
        max_profit_sim = None
        max_revenue_sim = None

        for i in range(steps + 1):
            price = price_min + i * step_size

            # 计算预期销量（基于价格弹性）
            price_ratio = price / market_avg
            volume_multiplier = price_ratio ** elasticity
            est_monthly_sales = int(base_monthly_sales * volume_multiplier)

            # 计算利润
            referral_fee = price * referral_pct
            return_cost = price * return_rate
            profit_per_unit = price - total_cost_usd - fba_fee - referral_fee - return_cost
            monthly_profit = profit_per_unit * est_monthly_sales
            monthly_revenue = price * est_monthly_sales
            margin = profit_per_unit / price * 100 if price > 0 else 0

            sim = {
                "price": round(price, 2),
                "est_monthly_sales": est_monthly_sales,
                "profit_per_unit": round(profit_per_unit, 2),
                "monthly_profit": round(monthly_profit, 2),
                "monthly_revenue": round(monthly_revenue, 2),
                "margin_pct": round(margin, 1),
                "price_vs_market": round((price / market_avg - 1) * 100, 1),
            }
            simulations.append(sim)

            if max_profit_sim is None or monthly_profit > max_profit_sim["monthly_profit"]:
                max_profit_sim = sim
            if max_revenue_sim is None or monthly_revenue > max_revenue_sim["monthly_revenue"]:
                max_revenue_sim = sim

        return {
            "market_avg_price": round(market_avg, 2),
            "base_monthly_sales": base_monthly_sales,
            "elasticity_coefficient": elasticity,
            "simulations": simulations,
            "max_profit_price": max_profit_sim,
            "max_revenue_price": max_revenue_sim,
            "chart_data": {
                "prices": [s["price"] for s in simulations],
                "monthly_profits": [s["monthly_profit"] for s in simulations],
                "monthly_sales": [s["est_monthly_sales"] for s in simulations],
                "margins": [s["margin_pct"] for s in simulations],
            },
        }

    def _estimate_base_sales(self, products: list[dict]) -> int:
        """从竞品数据估算基准月销量"""
        sales_estimates = []
        for p in products[:20]:
            est = p.get("est_sales_30d") or p.get("monthly_sales") or 0
            if est:
                sales_estimates.append(int(est))

        if sales_estimates:
            # 取中位数作为基准
            sales_estimates.sort()
            n = len(sales_estimates)
            return sales_estimates[n // 2]

        # 如果没有销量数据，用评论数估算
        review_counts = []
        for p in products[:20]:
            rc = p.get("review_count") or p.get("reviews") or 0
            if rc:
                review_counts.append(int(rc))

        if review_counts:
            avg_reviews = sum(review_counts) / len(review_counts)
            # 经验公式: 月销量 ≈ 评论数 × 0.05 × 30 / 365
            return max(int(avg_reviews * 0.05 * 30 / 365), 10)

        return 100  # 默认基准

    # ================================================================
    # 多策略对比
    # ================================================================

    def compare_strategies(self, cost_params: dict,
                            products: list[dict]) -> dict:
        """
        对比多种定价策略的预期效果

        :param cost_params: 成本参数
        :param products: 竞品产品列表
        :return: 策略对比结果
        """
        distribution = self.analyze_price_distribution(products)
        market_avg = distribution.get("statistics", {}).get("avg", 0)

        if not market_avg:
            return {"error": "No market price data available"}

        # 成本计算
        sourcing_rmb = cost_params.get("sourcing_cost_rmb", 0)
        shipping_rmb = cost_params.get("shipping_cost_per_kg", 0) * cost_params.get("weight_kg", 0.5)
        total_cost_usd = (sourcing_rmb + shipping_rmb) / self.exchange_rate
        fba_fee = cost_params.get("fba_fee", self.DEFAULT_FEE_RATES["fba_fee_estimate"])
        referral_pct = self.DEFAULT_FEE_RATES["referral_fee_pct"]
        return_rate = self.DEFAULT_FEE_RATES["return_rate"]

        base_sales = self._estimate_base_sales(products)
        elasticity = -2.0

        comparisons = []

        for strategy_key, strategy_def in self.STRATEGIES.items():
            price_low = market_avg * strategy_def["price_factor_range"][0]
            price_high = market_avg * strategy_def["price_factor_range"][1]
            price_mid = (price_low + price_high) / 2

            # 计算该策略下的预期销量
            price_ratio = price_mid / market_avg
            volume_multiplier = price_ratio ** elasticity
            est_sales = int(base_sales * volume_multiplier)

            # 计算利润
            referral_fee = price_mid * referral_pct
            return_cost = price_mid * return_rate
            profit_per_unit = price_mid - total_cost_usd - fba_fee - referral_fee - return_cost
            monthly_profit = profit_per_unit * est_sales
            margin = profit_per_unit / price_mid * 100 if price_mid > 0 else 0

            # 盈亏平衡判断
            breakeven = (total_cost_usd + fba_fee) / (1 - referral_pct - return_rate)
            is_profitable = price_mid > breakeven

            comparisons.append({
                "strategy": strategy_key,
                "name": strategy_def["name"],
                "description": strategy_def["description"],
                "suitable_for": strategy_def["suitable_for"],
                "risk": strategy_def["risk"],
                "price_range": {
                    "low": round(price_low, 2),
                    "mid": round(price_mid, 2),
                    "high": round(price_high, 2),
                },
                "price_vs_market": f"{((price_mid / market_avg - 1) * 100):+.1f}%",
                "est_monthly_sales": est_sales,
                "profit_per_unit": round(profit_per_unit, 2),
                "monthly_profit": round(monthly_profit, 2),
                "margin_pct": round(margin, 1),
                "is_profitable": is_profitable,
                "breakeven_price": round(breakeven, 2),
            })

        # 按月利润排序
        comparisons.sort(key=lambda x: x["monthly_profit"], reverse=True)

        # 推荐策略
        profitable = [c for c in comparisons if c["is_profitable"]]
        recommended = profitable[0] if profitable else comparisons[0]

        return {
            "market_avg_price": round(market_avg, 2),
            "base_monthly_sales": base_sales,
            "total_landed_cost_usd": round(total_cost_usd, 2),
            "comparisons": comparisons,
            "recommended_strategy": recommended["strategy"],
            "recommended_name": recommended["name"],
            "recommendation_reason": (
                f"在 {recommended['name']} 策略下，预计月利润 ${recommended['monthly_profit']:.2f}，"
                f"利润率 {recommended['margin_pct']:.1f}%，月销量 {recommended['est_monthly_sales']} 单"
            ),
            "chart_data": {
                "strategies": [c["name"] for c in comparisons],
                "monthly_profits": [c["monthly_profit"] for c in comparisons],
                "margins": [c["margin_pct"] for c in comparisons],
                "sales": [c["est_monthly_sales"] for c in comparisons],
            },
        }

    # ================================================================
    # 促销定价建议
    # ================================================================

    def suggest_promotions(self, current_price: float,
                            cost_params: dict,
                            products: list[dict]) -> dict:
        """
        生成促销定价建议

        :param current_price: 当前售价
        :param cost_params: 成本参数
        :param products: 竞品产品列表
        :return: 促销建议
        """
        sourcing_rmb = cost_params.get("sourcing_cost_rmb", 0)
        shipping_rmb = cost_params.get("shipping_cost_per_kg", 0) * cost_params.get("weight_kg", 0.5)
        total_cost_usd = (sourcing_rmb + shipping_rmb) / self.exchange_rate
        fba_fee = cost_params.get("fba_fee", self.DEFAULT_FEE_RATES["fba_fee_estimate"])
        referral_pct = self.DEFAULT_FEE_RATES["referral_fee_pct"]
        return_rate = self.DEFAULT_FEE_RATES["return_rate"]

        breakeven = (total_cost_usd + fba_fee) / (1 - referral_pct - return_rate)
        base_sales = self._estimate_base_sales(products)

        promotions = []

        # 1. Coupon 优惠券 (5%-15% off)
        for discount_pct in [5, 10, 15]:
            coupon_price = current_price * (1 - discount_pct / 100)
            if coupon_price > breakeven:
                referral = coupon_price * referral_pct
                ret_cost = coupon_price * return_rate
                profit = coupon_price - total_cost_usd - fba_fee - referral - ret_cost
                # Coupon 提升转化率约 10-30%
                sales_boost = 1 + discount_pct * 0.02
                est_sales = int(base_sales * sales_boost)

                promotions.append({
                    "type": "coupon",
                    "name": f"Coupon {discount_pct}% Off",
                    "discount_pct": discount_pct,
                    "effective_price": round(coupon_price, 2),
                    "profit_per_unit": round(profit, 2),
                    "est_sales_boost_pct": round((sales_boost - 1) * 100, 0),
                    "est_monthly_sales": est_sales,
                    "est_monthly_profit": round(profit * est_sales, 2),
                    "is_profitable": True,
                })

        # 2. Lightning Deal (通常需要降价 15-25%)
        for discount_pct in [15, 20, 25]:
            deal_price = current_price * (1 - discount_pct / 100)
            if deal_price > breakeven * 0.9:  # Lightning Deal 可以接受微亏
                referral = deal_price * referral_pct
                ret_cost = deal_price * return_rate
                profit = deal_price - total_cost_usd - fba_fee - referral - ret_cost
                # LD 期间销量可能增加 3-10 倍
                sales_boost = 3 + discount_pct * 0.2
                est_daily_sales = int(base_sales / 30 * sales_boost)

                promotions.append({
                    "type": "lightning_deal",
                    "name": f"Lightning Deal {discount_pct}% Off",
                    "discount_pct": discount_pct,
                    "effective_price": round(deal_price, 2),
                    "profit_per_unit": round(profit, 2),
                    "est_daily_sales": est_daily_sales,
                    "est_deal_profit": round(profit * est_daily_sales, 2),
                    "is_profitable": profit > 0,
                    "note": "Lightning Deal 费用约 $150-300/次",
                })

        # 3. Subscribe & Save (5%-10% off)
        for discount_pct in [5, 10]:
            sns_price = current_price * (1 - discount_pct / 100)
            referral = sns_price * referral_pct
            ret_cost = sns_price * return_rate
            profit = sns_price - total_cost_usd - fba_fee - referral - ret_cost

            promotions.append({
                "type": "subscribe_save",
                "name": f"Subscribe & Save {discount_pct}% Off",
                "discount_pct": discount_pct,
                "effective_price": round(sns_price, 2),
                "profit_per_unit": round(profit, 2),
                "is_profitable": profit > 0,
                "note": "适合复购率高的消耗品，提升客户终身价值",
            })

        return {
            "current_price": current_price,
            "breakeven_price": round(breakeven, 2),
            "promotions": promotions,
            "best_promotion": max(promotions, key=lambda p: p.get("est_monthly_profit", p.get("est_deal_profit", 0)))
            if promotions else None,
        }
