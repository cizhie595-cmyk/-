"""
AI 选品决策引擎 - Step 6 增强模块
整合所有分析数据，生成综合选品决策报告，包含风险评估、机会评分和可执行建议。
"""

import math
from datetime import datetime
from typing import Optional
from loguru import logger


class ProductDecisionEngine:
    """
    AI 选品决策引擎
    - 整合产品数据、竞品分析、利润计算、评论分析等多维数据
    - 生成综合选品评分（0-100）
    - 多维度风险评估
    - 可执行的选品建议
    - Go/No-Go 决策推荐
    """

    # 评分权重
    WEIGHTS = {
        "market_demand": 0.20,     # 市场需求（BSR、销量）
        "profit_potential": 0.25,  # 利润潜力
        "competition": 0.20,      # 竞争程度
        "product_quality": 0.15,  # 产品质量（评分、评论）
        "entry_feasibility": 0.10, # 进入可行性
        "risk_level": 0.10,       # 风险水平
    }

    def __init__(self, ai_client=None):
        """
        :param ai_client: AI API 客户端（可选，用于生成自然语言摘要）
        """
        self.ai_client = ai_client

    # ------------------------------------------------------------------
    # 综合决策评估
    # ------------------------------------------------------------------
    def evaluate_product(self, product_data: dict,
                         market_data: dict = None,
                         profit_data: dict = None,
                         review_data: dict = None,
                         competitor_data: dict = None) -> dict:
        """
        综合评估产品的选品价值
        :param product_data: 产品基础数据
        :param market_data: 市场/类目分析数据
        :param profit_data: 利润计算数据
        :param review_data: 评论分析数据
        :param competitor_data: 竞品分析数据
        :return: 综合决策报告
        """
        market_data = market_data or {}
        profit_data = profit_data or {}
        review_data = review_data or {}
        competitor_data = competitor_data or {}

        # 各维度评分
        scores = {
            "market_demand": self._score_market_demand(product_data, market_data),
            "profit_potential": self._score_profit_potential(profit_data),
            "competition": self._score_competition(competitor_data, market_data),
            "product_quality": self._score_product_quality(product_data, review_data),
            "entry_feasibility": self._score_entry_feasibility(product_data, competitor_data),
            "risk_level": self._score_risk_level(product_data, market_data, review_data),
        }

        # 加权总分
        total_score = sum(
            scores[dim] * weight
            for dim, weight in self.WEIGHTS.items()
        )
        total_score = round(total_score, 1)

        # 决策推荐
        decision = self._make_decision(total_score, scores)

        # 风险清单
        risks = self._identify_risks(product_data, market_data, profit_data,
                                      review_data, competitor_data)

        # 机会清单
        opportunities = self._identify_opportunities(
            product_data, market_data, profit_data, competitor_data
        )

        # 可执行建议
        action_items = self._generate_action_items(
            decision, scores, risks, opportunities
        )

        result = {
            "asin": product_data.get("asin") or product_data.get("product_id", ""),
            "title": product_data.get("title", ""),
            "overall_score": total_score,
            "decision": decision,
            "dimension_scores": scores,
            "risks": risks,
            "opportunities": opportunities,
            "action_items": action_items,
            "score_breakdown": self._build_score_breakdown(scores),
            "evaluated_at": datetime.now().isoformat(),
        }

        # 如果有 AI 客户端，生成自然语言摘要
        if self.ai_client:
            result["ai_summary"] = self._generate_ai_summary(result)

        return result

    # ------------------------------------------------------------------
    # 批量评估
    # ------------------------------------------------------------------
    def batch_evaluate(self, products: list[dict],
                       market_data: dict = None,
                       profit_results: list[dict] = None,
                       competitor_data: dict = None) -> dict:
        """
        批量评估多个产品，生成排名
        :param products: 产品列表
        :param market_data: 市场数据
        :param profit_results: 利润计算结果列表
        :param competitor_data: 竞品数据
        :return: 批量评估结果和排名
        """
        profit_map = {}
        if profit_results:
            for pr in profit_results:
                asin = pr.get("asin") or pr.get("product_id", "")
                if asin:
                    profit_map[asin] = pr

        evaluations = []
        for product in products:
            asin = product.get("asin") or product.get("product_id", "")
            profit = profit_map.get(asin, {})

            evaluation = self.evaluate_product(
                product_data=product,
                market_data=market_data,
                profit_data=profit,
                competitor_data=competitor_data,
            )
            evaluations.append(evaluation)

        # 按总分排序
        evaluations.sort(key=lambda x: x["overall_score"], reverse=True)

        # 添加排名
        for i, ev in enumerate(evaluations):
            ev["rank"] = i + 1

        # 统计
        go_count = sum(1 for e in evaluations if e["decision"]["recommendation"] == "GO")
        maybe_count = sum(1 for e in evaluations if e["decision"]["recommendation"] == "MAYBE")
        nogo_count = sum(1 for e in evaluations if e["decision"]["recommendation"] == "NO-GO")

        return {
            "total_evaluated": len(evaluations),
            "summary": {
                "go_count": go_count,
                "maybe_count": maybe_count,
                "nogo_count": nogo_count,
                "avg_score": round(
                    sum(e["overall_score"] for e in evaluations) / max(len(evaluations), 1), 1
                ),
                "top_score": evaluations[0]["overall_score"] if evaluations else 0,
            },
            "rankings": evaluations,
            "evaluated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 维度评分方法
    # ------------------------------------------------------------------
    def _score_market_demand(self, product: dict, market: dict) -> float:
        """评估市场需求 (0-100)"""
        score = 50  # 基础分

        # BSR 评分
        bsr = product.get("bsr_rank") or product.get("bsr", 0)
        if bsr:
            if bsr <= 1000:
                score += 30
            elif bsr <= 5000:
                score += 25
            elif bsr <= 20000:
                score += 15
            elif bsr <= 50000:
                score += 5
            else:
                score -= 10

        # 月销量评分
        sales = product.get("est_sales_30d") or product.get("monthly_sales", 0)
        if sales:
            if sales >= 1000:
                score += 20
            elif sales >= 500:
                score += 15
            elif sales >= 100:
                score += 10
            elif sales >= 30:
                score += 5

        # 市场规模
        market_size = market.get("market_size") or market.get("total_revenue", 0)
        if market_size and market_size > 1000000:
            score += 10
        elif market_size and market_size > 100000:
            score += 5

        # 市场增长趋势
        growth = market.get("growth_trend") or market.get("trend", "")
        if growth in ("increasing", "growing", "up"):
            score += 10
        elif growth in ("decreasing", "declining", "down"):
            score -= 10

        return min(max(score, 0), 100)

    def _score_profit_potential(self, profit: dict) -> float:
        """评估利润潜力 (0-100)"""
        score = 50

        # 利润率
        margin = profit.get("profit_margin_pct") or profit.get("margin_pct", 0)
        if not margin:
            # 尝试从嵌套结构获取
            profit_detail = profit.get("profit", {})
            margin = profit_detail.get("margin_pct", 0)

        if margin >= 30:
            score += 30
        elif margin >= 20:
            score += 20
        elif margin >= 15:
            score += 10
        elif margin >= 10:
            score += 5
        elif margin > 0:
            score -= 5
        else:
            score -= 20

        # 单件利润
        unit_profit = profit.get("profit_per_unit_usd") or profit.get("net_profit", 0)
        if not unit_profit:
            profit_detail = profit.get("profit", {})
            unit_profit = profit_detail.get("per_unit_usd", 0)

        if unit_profit >= 10:
            score += 15
        elif unit_profit >= 5:
            score += 10
        elif unit_profit >= 3:
            score += 5
        elif unit_profit > 0:
            score += 0
        else:
            score -= 15

        # ROI
        roi = profit.get("roi_pct") or profit.get("roi", 0)
        if not roi:
            profit_detail = profit.get("profit", {})
            roi = profit_detail.get("roi_pct", 0)

        if roi >= 100:
            score += 15
        elif roi >= 50:
            score += 10
        elif roi >= 30:
            score += 5

        return min(max(score, 0), 100)

    def _score_competition(self, competitor: dict, market: dict) -> float:
        """评估竞争程度 (0-100, 分数越高竞争越有利)"""
        score = 50

        # 市场集中度（HHI）
        concentration = competitor.get("market_concentration", {})
        hhi = concentration.get("hhi_index", 0)
        if not hhi:
            hhi = market.get("hhi_index", 0)

        if hhi < 1000:
            score += 15  # 分散市场，机会多
        elif hhi < 1500:
            score += 5
        elif hhi > 2500:
            score -= 15  # 高度集中，难以进入

        # 进入壁垒
        barriers = competitor.get("entry_barriers", {})
        barrier_level = barriers.get("overall_level", "")
        if barrier_level == "低":
            score += 20
        elif barrier_level == "中":
            score += 5
        elif barrier_level == "高":
            score -= 15

        # 竞品平均评论数
        avg_reviews = market.get("avg_review_count", 0)
        if avg_reviews < 50:
            score += 15
        elif avg_reviews < 200:
            score += 5
        elif avg_reviews > 1000:
            score -= 15

        return min(max(score, 0), 100)

    def _score_product_quality(self, product: dict, review: dict) -> float:
        """评估产品质量 (0-100)"""
        score = 50

        # 评分
        rating = product.get("rating", 0)
        if rating >= 4.5:
            score += 25
        elif rating >= 4.0:
            score += 15
        elif rating >= 3.5:
            score += 5
        elif rating >= 3.0:
            score -= 5
        elif rating > 0:
            score -= 20

        # 评论数量
        review_count = product.get("review_count", 0)
        if review_count >= 100:
            score += 10
        elif review_count >= 50:
            score += 5

        # 评论质量
        quality = review.get("review_quality", {})
        quality_score = quality.get("quality_score", 50)
        if quality_score >= 80:
            score += 15
        elif quality_score >= 60:
            score += 5
        elif quality_score < 40:
            score -= 10

        return min(max(score, 0), 100)

    def _score_entry_feasibility(self, product: dict,
                                  competitor: dict) -> float:
        """评估进入可行性 (0-100)"""
        score = 50

        # 价格门槛
        price = product.get("price") or product.get("price_current", 0)
        if price:
            if price >= 50:
                score += 10  # 高价产品利润空间大
            elif price >= 20:
                score += 15  # 中等价格最佳
            elif price >= 10:
                score += 5
            else:
                score -= 5  # 低价产品利润薄

        # 产品复杂度（通过类目推断）
        category = (product.get("bsr_category") or product.get("category", "")).lower()
        complex_categories = ["electronics", "appliances", "computers", "automotive"]
        simple_categories = ["home", "kitchen", "garden", "sports", "toys", "pet"]

        if any(c in category for c in simple_categories):
            score += 10
        elif any(c in category for c in complex_categories):
            score -= 10

        # FBA 可行性
        ft = (product.get("fulfillment_type") or product.get("fulfillment", "")).upper()
        if "FBA" in ft:
            score += 10  # 已有 FBA 先例

        # 竞品数量
        total_competitors = competitor.get("total_products", 0)
        if total_competitors < 50:
            score += 10
        elif total_competitors > 200:
            score -= 10

        return min(max(score, 0), 100)

    def _score_risk_level(self, product: dict, market: dict,
                          review: dict) -> float:
        """评估风险水平 (0-100, 分数越高风险越低)"""
        score = 70  # 基础分偏高

        # 季节性风险
        seasonality = market.get("seasonality", {})
        if seasonality.get("has_seasonality"):
            score -= 15

        # 评论质量风险
        quality = review.get("review_quality", {})
        risk_level = quality.get("risk_level", "")
        if risk_level == "critical":
            score -= 25
        elif risk_level == "high":
            score -= 15
        elif risk_level == "medium":
            score -= 5

        # 价格战风险
        price = product.get("price") or product.get("price_current", 0)
        if price and price < 10:
            score -= 10  # 低价产品容易陷入价格战

        # 品牌垄断风险
        concentration = market.get("market_concentration", {})
        hhi = concentration.get("hhi_index", 0)
        if hhi > 2500:
            score -= 15

        return min(max(score, 0), 100)

    # ------------------------------------------------------------------
    # 决策生成
    # ------------------------------------------------------------------
    def _make_decision(self, total_score: float, scores: dict) -> dict:
        """生成 Go/No-Go 决策"""
        if total_score >= 70:
            recommendation = "GO"
            confidence = "high"
            summary = "该产品具有较高的选品价值，建议进入市场。"
        elif total_score >= 50:
            recommendation = "MAYBE"
            confidence = "medium"
            summary = "该产品有一定潜力，但存在风险因素，建议进一步调研。"
        else:
            recommendation = "NO-GO"
            confidence = "high"
            summary = "该产品选品价值较低或风险过高，不建议进入。"

        # 关键驱动因素
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        strengths = [
            {"dimension": dim, "score": s}
            for dim, s in sorted_scores if s >= 65
        ]
        weaknesses = [
            {"dimension": dim, "score": s}
            for dim, s in sorted_scores if s < 40
        ]

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "total_score": total_score,
            "summary": summary,
            "key_strengths": strengths[:3],
            "key_weaknesses": weaknesses[:3],
        }

    def _identify_risks(self, product: dict, market: dict,
                        profit: dict, review: dict,
                        competitor: dict) -> list[dict]:
        """识别风险因素"""
        risks = []

        # 利润风险
        margin = profit.get("profit_margin_pct") or profit.get("margin_pct", 0)
        if not margin:
            profit_detail = profit.get("profit", {})
            margin = profit_detail.get("margin_pct", 0)
        if margin < 15:
            risks.append({
                "category": "profit",
                "severity": "high" if margin < 10 else "medium",
                "title": "利润率偏低",
                "detail": f"利润率仅 {margin:.1f}%，低于推荐的 15% 最低线",
                "mitigation": "优化供应链成本或提高售价",
            })

        # 竞争风险
        avg_reviews = market.get("avg_review_count", 0)
        if avg_reviews > 500:
            risks.append({
                "category": "competition",
                "severity": "high",
                "title": "评论壁垒高",
                "detail": f"竞品平均评论数 {avg_reviews:.0f}，新品难以追赶",
                "mitigation": "通过 Vine 计划和优质产品快速积累评论",
            })

        # 质量风险
        rating = product.get("rating", 0)
        if rating and rating < 3.5:
            risks.append({
                "category": "quality",
                "severity": "medium",
                "title": "同类产品评分偏低",
                "detail": f"平均评分 {rating}，说明品类存在质量痛点",
                "mitigation": "这也是机会 - 通过提升质量可获得差异化优势",
            })

        # 季节性风险
        seasonality = market.get("seasonality", {})
        if seasonality.get("has_seasonality"):
            risks.append({
                "category": "seasonality",
                "severity": "medium",
                "title": "季节性波动",
                "detail": seasonality.get("recommendation", "产品存在季节性波动"),
                "mitigation": "合理规划库存，旺季前备货，淡季控制库存",
            })

        return risks

    def _identify_opportunities(self, product: dict, market: dict,
                                 profit: dict, competitor: dict) -> list[dict]:
        """识别机会"""
        opportunities = []

        # 高利润机会
        margin = profit.get("profit_margin_pct") or profit.get("margin_pct", 0)
        if not margin:
            profit_detail = profit.get("profit", {})
            margin = profit_detail.get("margin_pct", 0)
        if margin >= 30:
            opportunities.append({
                "category": "profit",
                "impact": "high",
                "title": "高利润率产品",
                "detail": f"利润率 {margin:.1f}%，远超行业平均水平",
            })

        # 低竞争机会
        barriers = competitor.get("entry_barriers", {})
        if barriers.get("overall_level") == "低":
            opportunities.append({
                "category": "competition",
                "impact": "high",
                "title": "低进入壁垒",
                "detail": "市场进入壁垒低，适合新卖家快速切入",
            })

        # 品牌化机会
        concentration = market.get("market_concentration", {})
        if concentration.get("hhi_index", 0) < 1000:
            opportunities.append({
                "category": "branding",
                "impact": "medium",
                "title": "品牌建设机会",
                "detail": "市场高度分散，品牌化运营可快速建立市场地位",
            })

        # 质量提升机会
        rating = product.get("rating", 0)
        if rating and 3.0 <= rating < 4.0:
            opportunities.append({
                "category": "quality",
                "impact": "high",
                "title": "质量差异化机会",
                "detail": f"同类产品评分 {rating}，通过提升质量可获得显著竞争优势",
            })

        return opportunities

    def _generate_action_items(self, decision: dict, scores: dict,
                                risks: list, opportunities: list) -> list[dict]:
        """生成可执行建议"""
        items = []
        priority = 1

        if decision["recommendation"] == "GO":
            items.append({
                "priority": priority,
                "action": "确认供应商和样品",
                "detail": "联系 1688 供应商获取样品，验证产品质量",
                "timeline": "1-2 周",
            })
            priority += 1

            items.append({
                "priority": priority,
                "action": "计算精确成本",
                "detail": "获取实际运费、关税、FBA 费用报价",
                "timeline": "1 周",
            })
            priority += 1

            items.append({
                "priority": priority,
                "action": "准备 Listing",
                "detail": "撰写标题、Bullet Points、描述，拍摄产品图片",
                "timeline": "1-2 周",
            })
            priority += 1

        elif decision["recommendation"] == "MAYBE":
            # 针对弱项给出建议
            for weakness in decision.get("key_weaknesses", []):
                dim = weakness["dimension"]
                if dim == "competition":
                    items.append({
                        "priority": priority,
                        "action": "深入竞品分析",
                        "detail": "详细分析 Top 10 竞品的优劣势，寻找差异化切入点",
                        "timeline": "3-5 天",
                    })
                elif dim == "profit_potential":
                    items.append({
                        "priority": priority,
                        "action": "优化成本结构",
                        "detail": "寻找更多供应商报价，优化物流方案",
                        "timeline": "1 周",
                    })
                elif dim == "market_demand":
                    items.append({
                        "priority": priority,
                        "action": "验证市场需求",
                        "detail": "通过 PPC 测试广告验证关键词搜索量和转化率",
                        "timeline": "2 周",
                    })
                priority += 1

        else:  # NO-GO
            items.append({
                "priority": 1,
                "action": "寻找替代品类",
                "detail": "基于当前分析的经验，搜索相关但竞争更低的细分品类",
                "timeline": "1 周",
            })

        return items

    def _build_score_breakdown(self, scores: dict) -> list[dict]:
        """构建评分分解（用于雷达图）"""
        labels = {
            "market_demand": "市场需求",
            "profit_potential": "利润潜力",
            "competition": "竞争优势",
            "product_quality": "产品质量",
            "entry_feasibility": "进入可行性",
            "risk_level": "风险控制",
        }
        return [
            {
                "dimension": dim,
                "label": labels.get(dim, dim),
                "score": score,
                "weight": self.WEIGHTS.get(dim, 0),
                "weighted_score": round(score * self.WEIGHTS.get(dim, 0), 1),
            }
            for dim, score in scores.items()
        ]

    def _generate_ai_summary(self, evaluation: dict) -> str:
        """使用 AI 生成自然语言摘要"""
        try:
            prompt = (
                f"请根据以下选品评估数据，生成一段简洁的中文选品建议摘要（100-200字）：\n"
                f"产品: {evaluation.get('title', 'N/A')}\n"
                f"综合评分: {evaluation['overall_score']}/100\n"
                f"决策: {evaluation['decision']['recommendation']}\n"
                f"优势: {[s['dimension'] for s in evaluation['decision'].get('key_strengths', [])]}\n"
                f"劣势: {[w['dimension'] for w in evaluation['decision'].get('key_weaknesses', [])]}\n"
                f"风险数: {len(evaluation.get('risks', []))}\n"
                f"机会数: {len(evaluation.get('opportunities', []))}\n"
            )

            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "你是一位跨境电商选品专家，请用专业但简洁的语言给出选品建议。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"AI 摘要生成失败: {e}")
            return evaluation["decision"]["summary"]
