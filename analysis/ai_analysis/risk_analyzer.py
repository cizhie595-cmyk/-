"""
AI 综合分析总结与风险预警模块

整合所有分析结果，使用 AI 生成：
  - 选品综合评分（0-100）
  - 风险预警（侵权、合规、季节性、竞争等）
  - 差异化建议
  - 运营策略推荐
  - 最终选品决策建议
"""

import json
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()


class RiskAnalyzer:
    """
    风险预警分析器

    识别和评估产品选品过程中的各类风险：
      - 知识产权风险（专利、商标、版权）
      - 合规风险（FDA、FCC、UL 认证等）
      - 季节性风险
      - 竞争风险
      - 供应链风险
      - 价格战风险
    """

    # 需要特殊认证的类目关键词
    COMPLIANCE_KEYWORDS = {
        "FDA": ["food", "supplement", "cosmetic", "drug", "medical", "skincare",
                "sunscreen", "vitamin", "dietary", "health"],
        "FCC": ["electronic", "bluetooth", "wifi", "wireless", "radio", "charger",
                "adapter", "speaker", "headphone", "earbuds"],
        "UL": ["electrical", "battery", "power", "charger", "heater", "fan",
               "lamp", "light", "appliance"],
        "CPSC": ["children", "kids", "baby", "toy", "infant", "toddler",
                 "nursery", "crib", "stroller"],
        "EPA": ["pesticide", "disinfectant", "antimicrobial", "insect",
                "repellent", "sanitizer"],
        "DOT": ["hazmat", "flammable", "aerosol", "lithium", "battery",
                "chemical", "paint"],
    }

    # 高侵权风险关键词
    IP_RISK_KEYWORDS = [
        "disney", "marvel", "nike", "adidas", "apple", "samsung",
        "pokemon", "hello kitty", "nfl", "nba", "mlb",
        "gucci", "louis vuitton", "chanel", "prada",
        "patented", "trademark", "licensed", "branded",
    ]

    def __init__(self, ai_client=None, ai_model: str = "gpt-4.1-mini"):
        self.ai_client = ai_client
        self.ai_model = ai_model

    def analyze_risks(self, product_data: dict) -> dict:
        """
        对单个产品进行全面风险分析。

        :param product_data: 产品数据（包含详情、评论、利润等）
        :return: 风险分析报告
        """
        title = product_data.get("title", "")
        category = product_data.get("category", "")
        brand = product_data.get("brand", "")
        asin = product_data.get("asin", "")

        logger.info(f"[风险分析] 开始分析: {asin} | {title[:50]}")

        report = {
            "asin": asin,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "risks": [],
            "risk_score": 0,
        }

        # 1. 知识产权风险
        ip_risk = self._check_ip_risk(title, brand, product_data)
        report["ip_risk"] = ip_risk
        if ip_risk["level"] in ("高", "极高"):
            report["risks"].append(ip_risk)

        # 2. 合规认证风险
        compliance_risk = self._check_compliance_risk(title, category, product_data)
        report["compliance_risk"] = compliance_risk
        if compliance_risk["required_certifications"]:
            report["risks"].append(compliance_risk)

        # 3. 竞争风险
        competition_risk = self._check_competition_risk(product_data)
        report["competition_risk"] = competition_risk

        # 4. 价格战风险
        price_risk = self._check_price_war_risk(product_data)
        report["price_risk"] = price_risk

        # 5. 季节性风险
        seasonal_risk = self._check_seasonal_risk(product_data)
        report["seasonal_risk"] = seasonal_risk

        # 6. 供应链风险
        supply_risk = self._check_supply_chain_risk(product_data)
        report["supply_risk"] = supply_risk

        # 7. Listing 被跟卖风险
        hijack_risk = self._check_hijack_risk(product_data)
        report["hijack_risk"] = hijack_risk

        # 综合风险评分
        report["risk_score"] = self._calculate_overall_risk_score(report)
        report["risk_level"] = self._score_to_level(report["risk_score"])

        # AI 综合风险评估
        if self.ai_client:
            report["ai_risk_assessment"] = self._ai_risk_assessment(product_data, report)

        return report

    def _check_ip_risk(self, title: str, brand: str, data: dict) -> dict:
        """检查知识产权风险"""
        risk = {
            "type": "知识产权风险",
            "level": "低",
            "score": 0,
            "details": [],
        }

        title_lower = title.lower()
        brand_lower = brand.lower()

        # 检查标题中的品牌关键词
        for keyword in self.IP_RISK_KEYWORDS:
            if keyword in title_lower or keyword in brand_lower:
                risk["score"] += 30
                risk["details"].append(f"标题/品牌包含高风险关键词: {keyword}")

        # 检查是否有品牌注册（Brand Registry）
        if brand and brand != "Unknown" and brand != "Generic":
            risk["score"] += 10
            risk["details"].append(f"产品有注册品牌: {brand}，跟卖可能面临品牌投诉")

        # 检查是否有外观专利风险（独特设计）
        detail = data.get("detail", {}) or {}
        if detail.get("aplus_images"):
            risk["score"] += 5
            risk["details"].append("产品有A+内容，品牌保护意识强")

        if risk["score"] >= 40:
            risk["level"] = "极高"
        elif risk["score"] >= 25:
            risk["level"] = "高"
        elif risk["score"] >= 10:
            risk["level"] = "中"

        return risk

    def _check_compliance_risk(self, title: str, category: str, data: dict) -> dict:
        """检查合规认证风险"""
        risk = {
            "type": "合规认证风险",
            "level": "低",
            "score": 0,
            "required_certifications": [],
            "details": [],
        }

        text = f"{title} {category}".lower()

        for cert, keywords in self.COMPLIANCE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    if cert not in risk["required_certifications"]:
                        risk["required_certifications"].append(cert)
                        risk["score"] += 20
                        risk["details"].append(f"可能需要 {cert} 认证（关键词: {kw}）")
                    break

        if risk["score"] >= 40:
            risk["level"] = "高"
        elif risk["score"] >= 20:
            risk["level"] = "中"

        return risk

    def _check_competition_risk(self, data: dict) -> dict:
        """检查竞争风险"""
        risk = {"type": "竞争风险", "level": "低", "score": 0, "details": []}

        category_analysis = data.get("category_analysis", {})
        competition = category_analysis.get("competition", {})

        comp_level = competition.get("competition_level", "")
        if comp_level == "极高竞争":
            risk["score"] = 40
            risk["level"] = "极高"
            risk["details"].append("类目竞争极其激烈")
        elif comp_level == "高竞争":
            risk["score"] = 30
            risk["level"] = "高"
            risk["details"].append("类目竞争激烈")

        # 头部评论数
        top_reviews = competition.get("top_10_avg_reviews", 0)
        if top_reviews > 5000:
            risk["score"] += 15
            risk["details"].append(f"头部产品平均评论数{top_reviews}，新品追赶困难")

        monopoly = category_analysis.get("monopoly_index", {})
        if monopoly.get("index", 0) > 60:
            risk["score"] += 10
            risk["details"].append(f"类目垄断指数{monopoly['index']}，头部效应明显")

        risk["level"] = self._score_to_level(risk["score"])
        return risk

    def _check_price_war_risk(self, data: dict) -> dict:
        """检查价格战风险"""
        risk = {"type": "价格战风险", "level": "低", "score": 0, "details": []}

        profit_data = data.get("profit", {})
        margin = profit_data.get("profit", {}).get("profit_margin", "0%")

        try:
            margin_val = float(margin.replace("%", ""))
        except (ValueError, AttributeError):
            margin_val = 0

        if margin_val < 15:
            risk["score"] += 25
            risk["details"].append(f"利润率仅{margin}，价格战空间极小")
        elif margin_val < 25:
            risk["score"] += 10
            risk["details"].append(f"利润率{margin}，价格战承受能力有限")

        # 检查类目价格分布
        pricing = data.get("category_analysis", {}).get("pricing", {})
        if pricing:
            avg_price = pricing.get("avg_price", 0)
            if avg_price and avg_price < 15:
                risk["score"] += 15
                risk["details"].append(f"类目均价仅${avg_price}，低价竞争激烈")

        risk["level"] = self._score_to_level(risk["score"])
        return risk

    def _check_seasonal_risk(self, data: dict) -> dict:
        """检查季节性风险"""
        risk = {"type": "季节性风险", "level": "低", "score": 0, "details": []}

        seasonality = data.get("category_analysis", {}).get("seasonality", {})

        if seasonality.get("is_seasonal"):
            ratio = seasonality.get("seasonality_ratio", 1)
            risk["score"] = min(int(ratio * 10), 40)
            risk["details"].append(f"产品有明显季节性（波动比{ratio:.1f}x）")

            peak = seasonality.get("peak_months", [])
            low = seasonality.get("low_months", [])
            if peak:
                risk["details"].append(f"旺季月份: {peak}")
            if low:
                risk["details"].append(f"淡季月份: {low}，需注意库存管理")

        risk["level"] = self._score_to_level(risk["score"])
        return risk

    def _check_supply_chain_risk(self, data: dict) -> dict:
        """检查供应链风险"""
        risk = {"type": "供应链风险", "level": "低", "score": 0, "details": []}

        # 基于产品重量和尺寸评估物流难度
        product_info = data.get("profit", {}).get("product_info", {})
        weight = product_info.get("weight_lb", 0)

        if weight > 10:
            risk["score"] += 20
            risk["details"].append(f"产品较重({weight}lb)，物流成本高")
        elif weight > 5:
            risk["score"] += 10
            risk["details"].append(f"产品中等重量({weight}lb)")

        size_tier = product_info.get("size_tier", "")
        if "oversize" in size_tier:
            risk["score"] += 15
            risk["details"].append(f"产品属于超大尺寸({size_tier})，FBA费用高")

        risk["level"] = self._score_to_level(risk["score"])
        return risk

    def _check_hijack_risk(self, data: dict) -> dict:
        """检查被跟卖风险"""
        risk = {"type": "跟卖风险", "level": "低", "score": 0, "details": []}

        detail = data.get("detail", {}) or {}
        brand = data.get("brand", "")

        # 无品牌 = 高跟卖风险
        if not brand or brand in ("Unknown", "Generic", "Unbranded"):
            risk["score"] += 25
            risk["details"].append("产品无品牌保护，容易被跟卖")

        # 无A+内容 = 品牌注册可能不完善
        if not detail.get("aplus_images"):
            risk["score"] += 10
            risk["details"].append("无A+内容，品牌保护可能不完善")

        risk["level"] = self._score_to_level(risk["score"])
        return risk

    def _calculate_overall_risk_score(self, report: dict) -> int:
        """计算综合风险评分"""
        scores = []
        for key in ["ip_risk", "compliance_risk", "competition_risk",
                     "price_risk", "seasonal_risk", "supply_risk", "hijack_risk"]:
            risk = report.get(key, {})
            if isinstance(risk, dict):
                scores.append(risk.get("score", 0))

        if not scores:
            return 0

        # 加权平均（IP和合规风险权重更高）
        weights = [2.0, 2.0, 1.5, 1.0, 0.8, 0.8, 1.0]
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights[:len(scores)])

        return min(int(weighted_sum / total_weight), 100)

    @staticmethod
    def _score_to_level(score: int) -> str:
        """分数转风险等级"""
        if score >= 40:
            return "极高"
        elif score >= 25:
            return "高"
        elif score >= 15:
            return "中"
        else:
            return "低"

    def _ai_risk_assessment(self, product_data: dict, risk_report: dict) -> str:
        """AI 综合风险评估"""
        if not self.ai_client:
            return ""

        prompt = f"""You are an Amazon product risk analyst. Based on the following risk analysis data, provide a concise risk assessment in Chinese (200 words max).

Product: {product_data.get('title', 'Unknown')}
ASIN: {product_data.get('asin', '')}
Brand: {product_data.get('brand', '')}

Risk Summary:
- IP Risk: {json.dumps(risk_report.get('ip_risk', {}), ensure_ascii=False)}
- Compliance Risk: {json.dumps(risk_report.get('compliance_risk', {}), ensure_ascii=False)}
- Competition Risk: {json.dumps(risk_report.get('competition_risk', {}), ensure_ascii=False)}
- Price War Risk: {json.dumps(risk_report.get('price_risk', {}), ensure_ascii=False)}
- Overall Risk Score: {risk_report.get('risk_score', 0)}/100

Provide:
1. Top 3 risk concerns
2. Mitigation strategies for each
3. Go/No-Go recommendation"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[风险分析] AI 评估失败: {e}")
            return ""


class AIProductSummarizer:
    """
    AI 选品综合总结器

    整合所有分析模块的结果，生成最终的选品报告。
    """

    def __init__(self, ai_client=None, ai_model: str = "gpt-4.1-mini"):
        self.ai_client = ai_client
        self.ai_model = ai_model

    def generate_final_report(self, all_data: dict) -> dict:
        """
        生成最终选品综合报告。

        :param all_data: 所有分析数据的汇总
        :return: 最终报告
        """
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "product_score": self._calculate_product_score(all_data),
        }

        # 评分明细
        report["score_breakdown"] = self._score_breakdown(all_data)

        # 差异化建议
        report["differentiation_suggestions"] = self._suggest_differentiation(all_data)

        # 运营策略
        report["operation_strategy"] = self._suggest_operation_strategy(all_data)

        # AI 最终总结
        if self.ai_client:
            report["ai_final_summary"] = self._ai_final_summary(all_data, report)

        # 最终决策
        score = report["product_score"]
        if score >= 80:
            report["decision"] = "强烈推荐"
            report["decision_reason"] = "产品各项指标优秀，建议立即启动"
        elif score >= 60:
            report["decision"] = "推荐"
            report["decision_reason"] = "产品整体不错，注意规避已识别的风险"
        elif score >= 40:
            report["decision"] = "谨慎考虑"
            report["decision_reason"] = "产品存在一定风险，需要差异化策略"
        else:
            report["decision"] = "不推荐"
            report["decision_reason"] = "风险较高或利润不足，建议寻找其他产品"

        return report

    def _calculate_product_score(self, data: dict) -> int:
        """计算产品综合评分（0-100）"""
        score = 50  # 基础分

        # 利润维度（±20分）
        profit = data.get("profit", {}).get("profit", {})
        margin = profit.get("profit_margin", "0%")
        try:
            margin_val = float(str(margin).replace("%", ""))
        except (ValueError, TypeError):
            margin_val = 0

        if margin_val >= 40:
            score += 20
        elif margin_val >= 30:
            score += 15
        elif margin_val >= 20:
            score += 10
        elif margin_val >= 10:
            score += 0
        else:
            score -= 20

        # 竞争维度（±15分）
        competition = data.get("category_analysis", {}).get("competition", {})
        comp_level = competition.get("competition_level", "")
        if comp_level == "低竞争":
            score += 15
        elif comp_level == "中等竞争":
            score += 5
        elif comp_level == "高竞争":
            score -= 5
        elif comp_level == "极高竞争":
            score -= 15

        # 风险维度（±15分）
        risk_score = data.get("risk_analysis", {}).get("risk_score", 50)
        if risk_score < 15:
            score += 15
        elif risk_score < 30:
            score += 5
        elif risk_score > 50:
            score -= 15
        elif risk_score > 35:
            score -= 5

        # 市场机会维度（±10分）
        opportunity = data.get("category_analysis", {}).get("opportunity", {})
        opp_score = opportunity.get("opportunity_score", 50)
        if opp_score >= 70:
            score += 10
        elif opp_score >= 50:
            score += 5
        elif opp_score < 30:
            score -= 10

        return max(0, min(100, score))

    def _score_breakdown(self, data: dict) -> dict:
        """评分明细"""
        return {
            "profit": {
                "weight": "30%",
                "status": data.get("profit", {}).get("health_check", {}).get("grade", "N/A"),
            },
            "competition": {
                "weight": "25%",
                "status": data.get("category_analysis", {}).get("competition", {}).get("competition_level", "N/A"),
            },
            "risk": {
                "weight": "25%",
                "status": data.get("risk_analysis", {}).get("risk_level", "N/A"),
            },
            "opportunity": {
                "weight": "20%",
                "status": data.get("category_analysis", {}).get("opportunity", {}).get("grade", "N/A"),
            },
        }

    def _suggest_differentiation(self, data: dict) -> list[str]:
        """生成差异化建议"""
        suggestions = []

        # 基于评论痛点
        negative_reviews = data.get("deep_analysis", {}).get("negative_reviews", [])
        if negative_reviews:
            suggestions.append("基于差评分析，重点解决用户反馈的质量/功能痛点")

        # 基于 Listing 质量
        assessment = data.get("deep_analysis", {}).get("assessment", {})
        listing_quality = assessment.get("listing_quality", {})
        if listing_quality.get("score", 100) < 70:
            suggestions.append("竞品 Listing 质量一般，优质图片和A+内容可获得视觉优势")

        # 基于物流方式
        fulfillment = assessment.get("fulfillment_analysis", {})
        if fulfillment.get("type") == "FBM":
            suggestions.append("竞品使用FBM发货，FBA入场可获得Prime标志和配送优势")

        # 基于品牌集中度
        brand_conc = data.get("category_analysis", {}).get("brand_concentration", {})
        if not brand_conc.get("has_dominant_brand"):
            suggestions.append("市场无绝对主导品牌，建立品牌认知的机会窗口")

        if not suggestions:
            suggestions.append("建议从产品功能、包装设计、售后服务等方面寻找差异化切入点")

        return suggestions

    def _suggest_operation_strategy(self, data: dict) -> dict:
        """生成运营策略建议"""
        strategy = {
            "launch_phase": [],
            "growth_phase": [],
            "maintenance_phase": [],
        }

        # 启动期
        strategy["launch_phase"] = [
            "Vine 计划获取初始评论（建议30-50条）",
            "自动广告投放，收集关键词数据",
            "设置有竞争力的定价（可略低于市场均价10-15%）",
            "确保库存充足，避免断货影响排名",
        ]

        # 增长期
        strategy["growth_phase"] = [
            "手动广告精准投放高转化关键词",
            "逐步提价至目标价格",
            "优化 Listing（根据搜索词报告调整标题和关键词）",
            "申请品牌注册，开通A+内容",
        ]

        # 维护期
        strategy["maintenance_phase"] = [
            "监控竞品动态和价格变化",
            "定期更新图片和A+内容",
            "管理库存，避免长期仓储费",
            "拓展变体，扩大产品线",
        ]

        return strategy

    def _ai_final_summary(self, all_data: dict, report: dict) -> str:
        """AI 最终总结"""
        if not self.ai_client:
            return ""

        prompt = f"""You are a senior Amazon product selection consultant. Generate a final product selection report summary in Chinese (400 words max).

Product Score: {report['product_score']}/100
Decision: {report['decision']}
Score Breakdown: {json.dumps(report['score_breakdown'], ensure_ascii=False)}
Differentiation Suggestions: {json.dumps(report['differentiation_suggestions'], ensure_ascii=False)}

Product Info:
- Title: {all_data.get('title', 'N/A')}
- ASIN: {all_data.get('asin', 'N/A')}
- Price: ${all_data.get('price', 'N/A')}
- Brand: {all_data.get('brand', 'N/A')}

Provide a professional summary including:
1. Executive summary (2-3 sentences)
2. Key strengths and weaknesses
3. Recommended action plan (3-5 steps)
4. Expected timeline and investment
5. Final verdict with confidence level"""

        try:
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[AI总结] 最终总结生成失败: {e}")
            return ""
