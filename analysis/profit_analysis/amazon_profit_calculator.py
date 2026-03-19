"""
Amazon FBA 利润核算模块

精确计算 Amazon FBA 模式下的利润，包含：
  - Amazon 佣金（Referral Fee，按类目 8%-17%）
  - FBA 配送费（按尺寸和重量阶梯计费）
  - FBA 仓储费（月度 + 长期仓储费）
  - 广告费（PPC 预估）
  - 退货成本
  - 1688 采购成本 + 国际物流
  - 汇率换算
"""

import json
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()


class AmazonFBAProfitCalculator:
    """
    Amazon FBA 利润计算器

    基于 Amazon 2024-2025 费率标准，精确计算每个产品的利润。
    """

    # ================================================================
    # Amazon Referral Fee 佣金费率（按类目）
    # ================================================================

    REFERRAL_FEE_RATES = {
        "Amazon Device Accessories": 0.45,
        "Automotive": 0.12,
        "Baby Products": 0.08,
        "Backpacks, Handbags, Luggage": 0.15,
        "Beauty": 0.08,
        "Books": 0.15,
        "Camera & Photo": 0.08,
        "Cell Phone Devices": 0.08,
        "Clothing & Accessories": 0.17,
        "Computers": 0.08,
        "Consumer Electronics": 0.08,
        "Electronics Accessories": 0.15,
        "Furniture": 0.15,
        "Grocery & Gourmet Food": 0.08,
        "Health & Personal Care": 0.08,
        "Home & Garden": 0.15,
        "Industrial & Scientific": 0.12,
        "Jewelry": 0.20,
        "Kitchen": 0.15,
        "Musical Instruments": 0.15,
        "Office Products": 0.15,
        "Outdoors": 0.15,
        "Personal Computers": 0.06,
        "Pet Products": 0.15,
        "Shoes": 0.15,
        "Software & Computer Games": 0.15,
        "Sports": 0.15,
        "Tools & Home Improvement": 0.15,
        "Toys & Games": 0.15,
        "Video Games": 0.15,
        "Watches": 0.16,
        "Default": 0.15,
    }

    # 最低佣金（美元）
    MINIMUM_REFERRAL_FEE = 0.30

    # ================================================================
    # FBA 配送费（2024-2025 标准尺寸）
    # ================================================================

    FBA_FULFILLMENT_FEES = {
        "small_standard": [
            {"max_weight_oz": 4, "fee": 3.22},
            {"max_weight_oz": 8, "fee": 3.40},
            {"max_weight_oz": 12, "fee": 3.58},
            {"max_weight_oz": 16, "fee": 3.77},
        ],
        "large_standard": [
            {"max_weight_oz": 4, "fee": 3.86},
            {"max_weight_oz": 8, "fee": 4.08},
            {"max_weight_oz": 12, "fee": 4.24},
            {"max_weight_oz": 16, "fee": 4.75},
            {"max_weight_lb": 1.5, "fee": 5.40},
            {"max_weight_lb": 2, "fee": 5.69},
            {"max_weight_lb": 2.5, "fee": 6.10},
            {"max_weight_lb": 3, "fee": 6.39},
            {"max_weight_lb": 20, "fee": 7.17, "per_lb_over_3": 0.16},
        ],
        "small_oversize": [
            {"max_weight_lb": 70, "fee": 9.73, "per_lb_over_1": 0.42},
        ],
        "medium_oversize": [
            {"max_weight_lb": 150, "fee": 19.05, "per_lb_over_1": 0.42},
        ],
        "large_oversize": [
            {"max_weight_lb": 150, "fee": 89.98, "per_lb_over_90": 0.83},
        ],
        "special_oversize": [
            {"max_weight_lb": 999, "fee": 158.49, "per_lb_over_90": 0.83},
        ],
    }

    # ================================================================
    # FBA 仓储费（每立方英尺/月）
    # ================================================================

    STORAGE_FEES = {
        "standard": {
            "jan_sep": 0.87,   # 1月-9月
            "oct_dec": 2.40,   # 10月-12月（旺季）
        },
        "oversize": {
            "jan_sep": 0.56,
            "oct_dec": 1.40,
        },
    }

    # 长期仓储费附加费
    AGED_INVENTORY_SURCHARGE = {
        "271_to_365_days": 2.40,   # 每立方英尺
        "over_365_days": 6.90,     # 每立方英尺 或 $0.15/件（取较大值）
    }

    def __init__(self, marketplace: str = "US", exchange_rate: float = 7.25):
        """
        :param marketplace: 目标站点
        :param exchange_rate: 美元兑人民币汇率
        """
        self.marketplace = marketplace
        self.exchange_rate = exchange_rate

    def calculate_profit(self, params: dict) -> dict:
        """
        计算单个产品的利润。

        :param params: {
            "selling_price": float,       # 售价（美元）
            "category": str,              # Amazon 类目
            "weight_lb": float,           # 产品重量（磅）
            "length_in": float,           # 长（英寸）
            "width_in": float,            # 宽（英寸）
            "height_in": float,           # 高（英寸）
            "cogs_rmb": float,            # 采购成本（人民币）
            "shipping_rmb_per_kg": float, # 国际物流费（人民币/kg）
            "weight_kg": float,           # 重量（kg，用于物流计算）
            "ppc_cost_per_unit": float,   # 每单广告费（美元，可选）
            "return_rate": float,         # 退货率（0-1，可选）
            "monthly_units": int,         # 月销量（用于仓储费分摊）
        }
        :return: 利润明细
        """
        selling_price = params.get("selling_price", 0)
        category = params.get("category", "Default")

        # 兼容多种参数名：支持 API 路由和 Pipeline 两种调用方式
        # 重量：优先 weight_lb，其次从 weight_kg 转换
        weight_lb = params.get("weight_lb", 0)
        weight_kg = params.get("weight_kg", 0)
        if not weight_lb and weight_kg:
            weight_lb = weight_kg * 2.2046
        elif not weight_kg and weight_lb:
            weight_kg = weight_lb * 0.4536

        # 尺寸：优先英寸，其次从厘米转换（1 in = 2.54 cm）
        length_in = params.get("length_in", 0)
        width_in = params.get("width_in", 0)
        height_in = params.get("height_in", 0)
        if not length_in and params.get("length_cm"):
            length_in = params["length_cm"] / 2.54
        if not width_in and params.get("width_cm"):
            width_in = params["width_cm"] / 2.54
        if not height_in and params.get("height_cm"):
            height_in = params["height_cm"] / 2.54

        # 采购成本：兼容 cogs_rmb / sourcing_cost_rmb
        cogs_rmb = params.get("cogs_rmb", 0) or params.get("sourcing_cost_rmb", 0)

        # 物流费：兼容 shipping_rmb_per_kg / shipping_cost_per_kg
        shipping_rmb_per_kg = (
            params.get("shipping_rmb_per_kg", 0)
            or params.get("shipping_cost_per_kg", 0)
            or 40
        )

        # 广告费：兼容 ppc_cost_per_unit / estimated_cpa
        ppc_cost = params.get("ppc_cost_per_unit", 0) or params.get("estimated_cpa", 0)

        return_rate = params.get("return_rate", 0.03)
        monthly_units = params.get("monthly_units", 100)

        # 1. Amazon 佣金
        referral_fee = self._calc_referral_fee(selling_price, category)

        # 2. FBA 配送费
        size_tier = self._determine_size_tier(length_in, width_in, height_in, weight_lb)
        fba_fee = self._calc_fba_fee(size_tier, weight_lb)

        # 3. 仓储费（分摊到每件）
        volume_cuft = (length_in * width_in * height_in) / 1728
        storage_fee = self._calc_storage_fee(volume_cuft, monthly_units)

        # 4. 采购成本（转美元）
        cogs_usd = cogs_rmb / self.exchange_rate

        # 5. 国际物流（转美元）
        shipping_usd = (shipping_rmb_per_kg * weight_kg) / self.exchange_rate

        # 6. 退货成本
        return_cost = selling_price * return_rate * 0.5

        # 7. 广告费
        ad_cost = ppc_cost

        # 汇总
        total_cost = referral_fee + fba_fee + storage_fee + cogs_usd + shipping_usd + return_cost + ad_cost
        profit = selling_price - total_cost
        profit_margin = (profit / selling_price * 100) if selling_price > 0 else 0
        roi = (profit / (cogs_usd + shipping_usd) * 100) if (cogs_usd + shipping_usd) > 0 else 0

        result = {
            "selling_price": round(selling_price, 2),
            "currency": "USD",
            "costs": {
                "referral_fee": round(referral_fee, 2),
                "referral_fee_rate": f"{self._get_referral_rate(category)*100:.0f}%",
                "fba_fulfillment_fee": round(fba_fee, 2),
                "storage_fee_per_unit": round(storage_fee, 2),
                "cogs_usd": round(cogs_usd, 2),
                "cogs_rmb": round(cogs_rmb, 2),
                "international_shipping_usd": round(shipping_usd, 2),
                "international_shipping_rmb": round(shipping_rmb_per_kg * weight_kg, 2),
                "return_cost": round(return_cost, 2),
                "ppc_cost": round(ad_cost, 2),
                "total_cost": round(total_cost, 2),
            },
            "profit": {
                "profit_per_unit_usd": round(profit, 2),
                "profit_per_unit_rmb": round(profit * self.exchange_rate, 2),
                "profit_margin": f"{profit_margin:.1f}%",
                "roi": f"{roi:.1f}%",
                "monthly_profit_usd": round(profit * monthly_units, 2),
                "monthly_profit_rmb": round(profit * monthly_units * self.exchange_rate, 2),
            },
            "product_info": {
                "size_tier": size_tier,
                "weight_lb": weight_lb,
                "dimensions": f"{length_in}x{width_in}x{height_in} in",
                "category": category,
                "marketplace": self.marketplace,
            },
            "health_check": self._profit_health_check(profit_margin, roi, profit),
        }

        return result

    def batch_calculate(self, products: list[dict]) -> list[dict]:
        """批量计算多个产品的利润"""
        results = []
        for product in products:
            try:
                result = self.calculate_profit(product)
                result["asin"] = product.get("asin", "")
                result["title"] = product.get("title", "")
                results.append(result)
            except Exception as e:
                logger.error(f"[利润计算] 计算失败: {e}")
                results.append({"asin": product.get("asin", ""), "error": str(e)})

        return results

    def compare_pricing_strategies(self, base_params: dict,
                                    price_range: tuple = None) -> list[dict]:
        """
        对比不同定价策略下的利润。

        :param base_params: 基础参数
        :param price_range: 价格范围 (min, max)，默认为售价的 ±30%
        :return: 不同价格下的利润对比
        """
        selling_price = base_params.get("selling_price", 0)
        if not price_range:
            price_range = (selling_price * 0.7, selling_price * 1.3)

        step = (price_range[1] - price_range[0]) / 10
        results = []

        for i in range(11):
            test_price = round(price_range[0] + step * i, 2)
            params = {**base_params, "selling_price": test_price}
            result = self.calculate_profit(params)
            results.append({
                "price": test_price,
                "profit": result["profit"]["profit_per_unit_usd"],
                "margin": result["profit"]["profit_margin"],
                "roi": result["profit"]["roi"],
                "monthly_profit": result["profit"]["monthly_profit_usd"],
            })

        return results

    # ================================================================
    # 内部计算方法
    # ================================================================

    def _get_referral_rate(self, category: str) -> float:
        """获取类目佣金费率"""
        return self.REFERRAL_FEE_RATES.get(category, self.REFERRAL_FEE_RATES["Default"])

    def _calc_referral_fee(self, price: float, category: str) -> float:
        """计算 Referral Fee"""
        rate = self._get_referral_rate(category)
        fee = price * rate
        return max(fee, self.MINIMUM_REFERRAL_FEE)

    def _determine_size_tier(self, length: float, width: float,
                              height: float, weight_lb: float) -> str:
        """
        确定产品尺寸等级。

        Amazon 尺寸分级标准（2024）：
        - Small Standard: ≤15x12x0.75 in, ≤1 lb
        - Large Standard: ≤18x14x8 in, ≤20 lb
        - Small Oversize: ≤60x30x30 in, ≤70 lb
        - Medium Oversize: ≤108 in (longest side), ≤150 lb
        - Large Oversize: ≤108 in, ≤150 lb, girth > 130 in
        - Special Oversize: > 108 in or > 150 lb
        """
        dims = sorted([length, width, height], reverse=True)
        longest = dims[0] if dims else 0
        median = dims[1] if len(dims) > 1 else 0
        shortest = dims[2] if len(dims) > 2 else 0
        girth = 2 * (median + shortest) + longest

        if longest <= 15 and median <= 12 and shortest <= 0.75 and weight_lb <= 1:
            return "small_standard"
        elif longest <= 18 and median <= 14 and shortest <= 8 and weight_lb <= 20:
            return "large_standard"
        elif longest <= 60 and median <= 30 and shortest <= 30 and weight_lb <= 70:
            return "small_oversize"
        elif longest <= 108 and weight_lb <= 150 and girth <= 130:
            return "medium_oversize"
        elif longest <= 108 and weight_lb <= 150:
            return "large_oversize"
        else:
            return "special_oversize"

    def _calc_fba_fee(self, size_tier: str, weight_lb: float) -> float:
        """计算 FBA 配送费"""
        tiers = self.FBA_FULFILLMENT_FEES.get(size_tier, [])
        weight_oz = weight_lb * 16

        for tier in tiers:
            if "max_weight_oz" in tier and weight_oz <= tier["max_weight_oz"]:
                return tier["fee"]
            elif "max_weight_lb" in tier and weight_lb <= tier["max_weight_lb"]:
                base_fee = tier["fee"]
                # 超重附加费
                if "per_lb_over_3" in tier and weight_lb > 3:
                    base_fee += (weight_lb - 3) * tier["per_lb_over_3"]
                elif "per_lb_over_1" in tier and weight_lb > 1:
                    base_fee += (weight_lb - 1) * tier["per_lb_over_1"]
                elif "per_lb_over_90" in tier and weight_lb > 90:
                    base_fee += (weight_lb - 90) * tier["per_lb_over_90"]
                return base_fee

        # 默认返回最后一级的费用
        if tiers:
            return tiers[-1]["fee"]
        return 5.00  # 默认值

    def _calc_storage_fee(self, volume_cuft: float, monthly_units: int) -> float:
        """
        计算月度仓储费（分摊到每件）。

        Amazon 仓储费按 "每立方英尺/月" 计费，这里是单件产品的体积对应的月度费用。
        volume_cuft 已经是单件产品的体积，所以 volume_cuft * rate 就是单件的月度仓储费。
        """
        month = datetime.now().month
        size_type = "standard"  # 简化处理

        if 1 <= month <= 9:
            rate = self.STORAGE_FEES[size_type]["jan_sep"]
        else:
            rate = self.STORAGE_FEES[size_type]["oct_dec"]

        # 单件产品的月度仓储费 = 单件体积 * 费率
        per_unit_storage = volume_cuft * rate
        return per_unit_storage

    def _profit_health_check(self, margin: float, roi: float,
                              profit: float) -> dict:
        """利润健康度检查"""
        issues = []
        grade = "A"

        if profit < 0:
            grade = "F"
            issues.append("产品亏损，需要调整定价或降低成本")
        elif margin < 10:
            grade = "D"
            issues.append("利润率低于10%，抗风险能力弱")
        elif margin < 20:
            grade = "C"
            issues.append("利润率低于20%，建议优化成本结构")
        elif margin < 30:
            grade = "B"
            issues.append("利润率尚可，有一定优化空间")

        if roi < 50:
            if grade > "C":
                grade = "C"
            issues.append("ROI 低于50%，资金使用效率不高")

        if not issues:
            issues.append("利润健康，产品值得运营")

        return {
            "grade": grade,
            "margin_status": "健康" if margin >= 30 else "一般" if margin >= 15 else "偏低" if margin >= 0 else "亏损",
            "roi_status": "优秀" if roi >= 100 else "良好" if roi >= 50 else "一般" if roi >= 0 else "亏损",
            "issues": issues,
        }
