"""
供应商评分系统 (Supplier Scorer)

Step 8 扩展模块 - 1688 供应商可靠性评分、多维度评估、对比矩阵

功能:
1. 供应商基础信息评分（经营年限、注册资本、认证资质）
2. 产品能力评分（SKU 数量、定制能力、起订量灵活性）
3. 服务能力评分（响应速度、退货率、物流时效）
4. 价格竞争力评分（价格水平、阶梯价优惠、付款条件）
5. 综合评分和供应商排名
6. 供应商对比矩阵生成
"""

import json
from datetime import datetime
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class SupplierScorer:
    """
    1688 供应商评分系统

    对 1688 搜索到的供应商进行多维度评分，
    帮助卖家选择最优供应商。
    """

    # 评分维度权重
    DIMENSION_WEIGHTS = {
        "credibility": 0.25,     # 信誉资质
        "product_capability": 0.25,  # 产品能力
        "service_quality": 0.20,  # 服务质量
        "price_competitiveness": 0.20,  # 价格竞争力
        "logistics": 0.10,       # 物流能力
    }

    def __init__(self, ai_client=None):
        """
        :param ai_client: OpenAI 客户端（用于 AI 辅助评估）
        """
        self.ai_client = ai_client

    # ================================================================
    # 单维度评分
    # ================================================================

    def score_credibility(self, supplier: dict) -> dict:
        """
        信誉资质评分

        评估指标:
        - 经营年限（越长越好）
        - 注册资本（越高越好）
        - 认证资质（ISO、SGS 等）
        - 1688 诚信通年限
        - 实力商家/超级工厂标签
        """
        score = 0
        details = {}

        # 经营年限 (0-25分)
        years = supplier.get("business_years") or supplier.get("years_in_business", 0)
        if years >= 10:
            year_score = 25
        elif years >= 5:
            year_score = 20
        elif years >= 3:
            year_score = 15
        elif years >= 1:
            year_score = 10
        else:
            year_score = 5
        score += year_score
        details["business_years"] = {"value": years, "score": year_score, "max": 25}

        # 注册资本 (0-20分)
        capital = supplier.get("registered_capital", 0)
        if isinstance(capital, str):
            # 解析 "500万" 格式
            import re
            match = re.search(r"(\d+(?:\.\d+)?)", capital.replace(",", ""))
            capital = float(match.group(1)) if match else 0
            if "万" in str(supplier.get("registered_capital", "")):
                capital *= 10000

        if capital >= 10000000:  # 1000万+
            cap_score = 20
        elif capital >= 5000000:
            cap_score = 16
        elif capital >= 1000000:
            cap_score = 12
        elif capital >= 500000:
            cap_score = 8
        else:
            cap_score = 4
        score += cap_score
        details["registered_capital"] = {"value": capital, "score": cap_score, "max": 20}

        # 认证资质 (0-25分)
        certifications = supplier.get("certifications", [])
        if isinstance(certifications, str):
            certifications = [c.strip() for c in certifications.split(",") if c.strip()]

        cert_score = 0
        high_value_certs = {"ISO9001", "ISO14001", "SGS", "CE", "FDA", "UL", "BSCI", "GMP"}
        for cert in certifications:
            cert_upper = cert.upper().replace(" ", "")
            if any(hvc in cert_upper for hvc in high_value_certs):
                cert_score += 5
            else:
                cert_score += 2
        cert_score = min(cert_score, 25)
        score += cert_score
        details["certifications"] = {
            "value": certifications,
            "count": len(certifications),
            "score": cert_score,
            "max": 25,
        }

        # 诚信通年限 (0-15分)
        trust_years = supplier.get("trust_pass_years") or supplier.get("chengxintong_years", 0)
        if trust_years >= 8:
            trust_score = 15
        elif trust_years >= 5:
            trust_score = 12
        elif trust_years >= 3:
            trust_score = 9
        elif trust_years >= 1:
            trust_score = 6
        else:
            trust_score = 0
        score += trust_score
        details["trust_pass_years"] = {"value": trust_years, "score": trust_score, "max": 15}

        # 特殊标签 (0-15分)
        tags = supplier.get("tags", []) or supplier.get("badges", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        tag_score = 0
        tag_values = {
            "超级工厂": 8, "super_factory": 8,
            "实力商家": 6, "power_merchant": 6,
            "金品诚企": 5, "gold_supplier": 5,
            "源头工厂": 4, "factory_direct": 4,
        }
        for tag in tags:
            for key, val in tag_values.items():
                if key in tag.lower():
                    tag_score += val
                    break
        tag_score = min(tag_score, 15)
        score += tag_score
        details["special_tags"] = {"value": tags, "score": tag_score, "max": 15}

        return {
            "dimension": "credibility",
            "score": min(score, 100),
            "max_score": 100,
            "details": details,
        }

    def score_product_capability(self, supplier: dict) -> dict:
        """
        产品能力评分

        评估指标:
        - SKU 数量
        - 是否支持定制/OEM/ODM
        - 起订量灵活性
        - 产品质量评分（买家评价）
        - 样品支持
        """
        score = 0
        details = {}

        # SKU 数量 (0-20分)
        sku_count = supplier.get("sku_count") or supplier.get("product_count", 0)
        if sku_count >= 500:
            sku_score = 20
        elif sku_count >= 200:
            sku_score = 16
        elif sku_count >= 50:
            sku_score = 12
        elif sku_count >= 10:
            sku_score = 8
        else:
            sku_score = 4
        score += sku_score
        details["sku_count"] = {"value": sku_count, "score": sku_score, "max": 20}

        # 定制能力 (0-25分)
        custom_score = 0
        if supplier.get("supports_oem") or supplier.get("oem"):
            custom_score += 10
        if supplier.get("supports_odm") or supplier.get("odm"):
            custom_score += 10
        if supplier.get("supports_custom_packaging") or supplier.get("custom_packaging"):
            custom_score += 5
        score += custom_score
        details["customization"] = {
            "oem": bool(supplier.get("supports_oem") or supplier.get("oem")),
            "odm": bool(supplier.get("supports_odm") or supplier.get("odm")),
            "custom_packaging": bool(supplier.get("supports_custom_packaging") or supplier.get("custom_packaging")),
            "score": custom_score,
            "max": 25,
        }

        # 起订量灵活性 (0-20分)
        moq = supplier.get("moq") or supplier.get("min_order_quantity", 0)
        if isinstance(moq, str):
            import re
            match = re.search(r"(\d+)", moq.replace(",", ""))
            moq = int(match.group(1)) if match else 0

        if moq <= 10:
            moq_score = 20
        elif moq <= 50:
            moq_score = 16
        elif moq <= 200:
            moq_score = 12
        elif moq <= 500:
            moq_score = 8
        else:
            moq_score = 4
        score += moq_score
        details["moq"] = {"value": moq, "score": moq_score, "max": 20}

        # 买家评价/复购率 (0-20分)
        buyer_rating = supplier.get("buyer_rating") or supplier.get("product_rating", 0)
        if buyer_rating >= 4.8:
            rating_score = 20
        elif buyer_rating >= 4.5:
            rating_score = 16
        elif buyer_rating >= 4.0:
            rating_score = 12
        elif buyer_rating >= 3.5:
            rating_score = 8
        else:
            rating_score = 4
        score += rating_score
        details["buyer_rating"] = {"value": buyer_rating, "score": rating_score, "max": 20}

        # 样品支持 (0-15分)
        sample_score = 0
        if supplier.get("free_sample") or supplier.get("sample_free"):
            sample_score = 15
        elif supplier.get("sample_available") or supplier.get("supports_sample"):
            sample_score = 10
        score += sample_score
        details["sample_support"] = {
            "free_sample": bool(supplier.get("free_sample") or supplier.get("sample_free")),
            "available": bool(supplier.get("sample_available") or supplier.get("supports_sample")),
            "score": sample_score,
            "max": 15,
        }

        return {
            "dimension": "product_capability",
            "score": min(score, 100),
            "max_score": 100,
            "details": details,
        }

    def score_service_quality(self, supplier: dict) -> dict:
        """
        服务质量评分

        评估指标:
        - 响应速度
        - 退货率/纠纷率
        - 交货准时率
        - 售后服务
        """
        score = 0
        details = {}

        # 响应速度 (0-30分)
        response_time = supplier.get("response_time_hours") or supplier.get("avg_response_hours", 24)
        if response_time <= 2:
            resp_score = 30
        elif response_time <= 6:
            resp_score = 24
        elif response_time <= 12:
            resp_score = 18
        elif response_time <= 24:
            resp_score = 12
        else:
            resp_score = 6
        score += resp_score
        details["response_time"] = {"value_hours": response_time, "score": resp_score, "max": 30}

        # 纠纷率 (0-25分)
        dispute_rate = supplier.get("dispute_rate", 0.05)
        if isinstance(dispute_rate, str):
            dispute_rate = float(dispute_rate.replace("%", "")) / 100
        if dispute_rate <= 0.01:
            dispute_score = 25
        elif dispute_rate <= 0.03:
            dispute_score = 20
        elif dispute_rate <= 0.05:
            dispute_score = 15
        elif dispute_rate <= 0.10:
            dispute_score = 8
        else:
            dispute_score = 0
        score += dispute_score
        details["dispute_rate"] = {"value": dispute_rate, "score": dispute_score, "max": 25}

        # 交货准时率 (0-25分)
        on_time_rate = supplier.get("on_time_delivery_rate") or supplier.get("delivery_rate", 0.9)
        if isinstance(on_time_rate, str):
            on_time_rate = float(on_time_rate.replace("%", "")) / 100
        if on_time_rate >= 0.98:
            delivery_score = 25
        elif on_time_rate >= 0.95:
            delivery_score = 20
        elif on_time_rate >= 0.90:
            delivery_score = 15
        elif on_time_rate >= 0.80:
            delivery_score = 10
        else:
            delivery_score = 5
        score += delivery_score
        details["on_time_delivery"] = {"value": on_time_rate, "score": delivery_score, "max": 25}

        # 售后服务 (0-20分)
        after_sale_score = 0
        if supplier.get("warranty") or supplier.get("quality_guarantee"):
            after_sale_score += 10
        if supplier.get("return_policy") or supplier.get("easy_return"):
            after_sale_score += 10
        score += after_sale_score
        details["after_sale"] = {
            "warranty": bool(supplier.get("warranty") or supplier.get("quality_guarantee")),
            "return_policy": bool(supplier.get("return_policy") or supplier.get("easy_return")),
            "score": after_sale_score,
            "max": 20,
        }

        return {
            "dimension": "service_quality",
            "score": min(score, 100),
            "max_score": 100,
            "details": details,
        }

    def score_price_competitiveness(self, supplier: dict,
                                     market_avg_price: float = 0) -> dict:
        """
        价格竞争力评分

        评估指标:
        - 价格水平（与市场均价对比）
        - 阶梯价优惠幅度
        - 付款条件灵活性
        """
        score = 0
        details = {}

        # 价格水平 (0-40分)
        price = supplier.get("price") or supplier.get("unit_price", 0)
        if isinstance(price, str):
            import re
            match = re.search(r"(\d+(?:\.\d+)?)", price.replace(",", ""))
            price = float(match.group(1)) if match else 0

        if market_avg_price > 0 and price > 0:
            price_ratio = price / market_avg_price
            if price_ratio <= 0.7:
                price_score = 40
            elif price_ratio <= 0.85:
                price_score = 32
            elif price_ratio <= 1.0:
                price_score = 24
            elif price_ratio <= 1.15:
                price_score = 16
            else:
                price_score = 8
        else:
            price_score = 20  # 无法比较时给中间分
        score += price_score
        details["price_level"] = {
            "unit_price": price,
            "market_avg": market_avg_price,
            "score": price_score,
            "max": 40,
        }

        # 阶梯价优惠 (0-30分)
        tier_pricing = supplier.get("tier_pricing") or supplier.get("volume_discount", [])
        if tier_pricing:
            if isinstance(tier_pricing, list) and len(tier_pricing) >= 3:
                tier_score = 30
            elif isinstance(tier_pricing, list) and len(tier_pricing) >= 2:
                tier_score = 22
            elif tier_pricing:
                tier_score = 15
            else:
                tier_score = 0
        else:
            tier_score = 0
        score += tier_score
        details["tier_pricing"] = {
            "tiers": tier_pricing if isinstance(tier_pricing, list) else [],
            "score": tier_score,
            "max": 30,
        }

        # 付款条件 (0-30分)
        payment_score = 0
        payment_methods = supplier.get("payment_methods", [])
        if isinstance(payment_methods, str):
            payment_methods = [p.strip() for p in payment_methods.split(",")]

        # 支持信用担保/账期
        if supplier.get("credit_payment") or supplier.get("trade_assurance"):
            payment_score += 15
        # 支持多种支付方式
        if len(payment_methods) >= 3:
            payment_score += 10
        elif len(payment_methods) >= 1:
            payment_score += 5
        # 支持小额支付
        if supplier.get("small_amount_ok") or supplier.get("flexible_payment"):
            payment_score += 5
        payment_score = min(payment_score, 30)
        score += payment_score
        details["payment"] = {
            "methods": payment_methods,
            "trade_assurance": bool(supplier.get("credit_payment") or supplier.get("trade_assurance")),
            "score": payment_score,
            "max": 30,
        }

        return {
            "dimension": "price_competitiveness",
            "score": min(score, 100),
            "max_score": 100,
            "details": details,
        }

    def score_logistics(self, supplier: dict) -> dict:
        """
        物流能力评分

        评估指标:
        - 发货速度
        - 物流方式多样性
        - 跨境物流经验
        """
        score = 0
        details = {}

        # 发货速度 (0-40分)
        lead_time_days = supplier.get("lead_time_days") or supplier.get("shipping_days", 7)
        if lead_time_days <= 2:
            ship_score = 40
        elif lead_time_days <= 5:
            ship_score = 32
        elif lead_time_days <= 7:
            ship_score = 24
        elif lead_time_days <= 14:
            ship_score = 16
        else:
            ship_score = 8
        score += ship_score
        details["lead_time"] = {"value_days": lead_time_days, "score": ship_score, "max": 40}

        # 物流方式 (0-30分)
        shipping_methods = supplier.get("shipping_methods", [])
        if isinstance(shipping_methods, str):
            shipping_methods = [s.strip() for s in shipping_methods.split(",")]

        method_score = min(len(shipping_methods) * 8, 30)
        score += method_score
        details["shipping_methods"] = {
            "methods": shipping_methods,
            "count": len(shipping_methods),
            "score": method_score,
            "max": 30,
        }

        # 跨境经验 (0-30分)
        cross_border_score = 0
        if supplier.get("export_experience") or supplier.get("cross_border"):
            cross_border_score += 15
        if supplier.get("fba_shipping") or supplier.get("supports_fba_direct"):
            cross_border_score += 15
        elif supplier.get("international_shipping"):
            cross_border_score += 10
        score += cross_border_score
        details["cross_border"] = {
            "export_experience": bool(supplier.get("export_experience") or supplier.get("cross_border")),
            "fba_direct": bool(supplier.get("fba_shipping") or supplier.get("supports_fba_direct")),
            "score": cross_border_score,
            "max": 30,
        }

        return {
            "dimension": "logistics",
            "score": min(score, 100),
            "max_score": 100,
            "details": details,
        }

    # ================================================================
    # 综合评分
    # ================================================================

    def score_supplier(self, supplier: dict,
                        market_avg_price: float = 0) -> dict:
        """
        对供应商进行综合评分

        :param supplier: 供应商数据字典
        :param market_avg_price: 市场平均价格（用于价格竞争力对比）
        :return: 综合评分结果
        """
        dimensions = {
            "credibility": self.score_credibility(supplier),
            "product_capability": self.score_product_capability(supplier),
            "service_quality": self.score_service_quality(supplier),
            "price_competitiveness": self.score_price_competitiveness(supplier, market_avg_price),
            "logistics": self.score_logistics(supplier),
        }

        # 加权综合分
        total_score = 0
        for dim_name, weight in self.DIMENSION_WEIGHTS.items():
            dim_score = dimensions.get(dim_name, {}).get("score", 0)
            total_score += dim_score * weight

        # 评级
        if total_score >= 85:
            grade = "A+"
            recommendation = "优质供应商，强烈推荐合作"
        elif total_score >= 75:
            grade = "A"
            recommendation = "良好供应商，推荐合作"
        elif total_score >= 65:
            grade = "B+"
            recommendation = "合格供应商，可以考虑"
        elif total_score >= 55:
            grade = "B"
            recommendation = "一般供应商，建议多方对比"
        elif total_score >= 45:
            grade = "C"
            recommendation = "较弱供应商，谨慎选择"
        else:
            grade = "D"
            recommendation = "不推荐，建议寻找替代供应商"

        # 找出优势和劣势
        dim_scores = [(name, dim.get("score", 0)) for name, dim in dimensions.items()]
        dim_scores.sort(key=lambda x: x[1], reverse=True)
        strengths = [
            {"dimension": name, "score": s}
            for name, s in dim_scores if s >= 70
        ]
        weaknesses = [
            {"dimension": name, "score": s}
            for name, s in dim_scores if s < 50
        ]

        return {
            "supplier_name": supplier.get("name") or supplier.get("shop_name", "Unknown"),
            "supplier_url": supplier.get("url") or supplier.get("shop_url", ""),
            "total_score": round(total_score, 1),
            "grade": grade,
            "recommendation": recommendation,
            "dimensions": dimensions,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "scored_at": datetime.now().isoformat(),
        }

    # ================================================================
    # 批量评分和对比矩阵
    # ================================================================

    def score_multiple_suppliers(self, suppliers: list[dict],
                                  market_avg_price: float = 0) -> list[dict]:
        """
        批量评分多个供应商并排名

        :param suppliers: 供应商列表
        :param market_avg_price: 市场平均价格
        :return: 排名后的评分列表
        """
        results = []
        for supplier in suppliers:
            result = self.score_supplier(supplier, market_avg_price)
            results.append(result)

        # 按总分降序排列
        results.sort(key=lambda x: x["total_score"], reverse=True)

        # 添加排名
        for i, result in enumerate(results):
            result["rank"] = i + 1

        return results

    def generate_comparison_matrix(self, suppliers: list[dict],
                                    market_avg_price: float = 0) -> dict:
        """
        生成供应商对比矩阵

        :param suppliers: 供应商列表
        :param market_avg_price: 市场平均价格
        :return: 对比矩阵数据
        """
        scored = self.score_multiple_suppliers(suppliers, market_avg_price)

        matrix = {
            "generated_at": datetime.now().isoformat(),
            "supplier_count": len(scored),
            "market_avg_price": market_avg_price,
            "rankings": scored,
            "dimension_comparison": {},
            "best_in_class": {},
            "insights": [],
        }

        # 各维度对比
        for dim_name in self.DIMENSION_WEIGHTS:
            dim_data = []
            for s in scored:
                dim = s.get("dimensions", {}).get(dim_name, {})
                dim_data.append({
                    "supplier": s["supplier_name"],
                    "score": dim.get("score", 0),
                })
            dim_data.sort(key=lambda x: x["score"], reverse=True)
            matrix["dimension_comparison"][dim_name] = dim_data

            # 各维度最佳
            if dim_data:
                matrix["best_in_class"][dim_name] = dim_data[0]

        # 生成洞察
        if scored:
            best = scored[0]
            worst = scored[-1]
            matrix["insights"].append(
                f"最优供应商: {best['supplier_name']} (总分 {best['total_score']:.1f}, 等级 {best['grade']})"
            )

            if len(scored) > 1:
                score_gap = best["total_score"] - worst["total_score"]
                matrix["insights"].append(
                    f"供应商质量差距: {score_gap:.1f} 分 "
                    f"({best['grade']} vs {worst['grade']})"
                )

            # 价格最低的供应商
            price_dim = matrix["dimension_comparison"].get("price_competitiveness", [])
            if price_dim:
                matrix["insights"].append(
                    f"价格最优: {price_dim[0]['supplier']} "
                    f"(价格竞争力 {price_dim[0]['score']} 分)"
                )

        return matrix
