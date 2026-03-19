"""
顶层风险评分模块 - 五维风险雷达图

提供产品选品风险的五维评分体系：
  1. 竞争风险（Competition）
  2. 需求风险（Demand）
  3. 利润风险（Profit）
  4. 知识产权风险（IP Risk）
  5. 季节性风险（Seasonality）

每个维度评分 0-100，分数越高表示风险越大。
同时提供综合风险等级和建议。

使用方式:
    from analysis.risk_scoring import RiskScoring, FiveDimensionRadar
    scorer = RiskScoring()
    radar = scorer.calculate_radar(product_data)
"""

from typing import Optional
from datetime import datetime

from utils.logger import get_logger
from analysis.ai_analysis.risk_analyzer import RiskAnalyzer, AIProductSummarizer

logger = get_logger()

# 重导出核心类
__all__ = ["RiskScoring", "FiveDimensionRadar", "RiskAnalyzer"]


class FiveDimensionRadar:
    """
    五维风险雷达图数据结构

    Attributes:
        competition: 竞争风险分数 (0-100)
        demand: 需求风险分数 (0-100)
        profit: 利润风险分数 (0-100)
        ip_risk: 知识产权风险分数 (0-100)
        seasonality: 季节性风险分数 (0-100)
    """

    def __init__(
        self,
        competition: float = 0,
        demand: float = 0,
        profit: float = 0,
        ip_risk: float = 0,
        seasonality: float = 0,
    ):
        self.competition = min(max(competition, 0), 100)
        self.demand = min(max(demand, 0), 100)
        self.profit = min(max(profit, 0), 100)
        self.ip_risk = min(max(ip_risk, 0), 100)
        self.seasonality = min(max(seasonality, 0), 100)

    @property
    def overall_score(self) -> float:
        """加权综合风险评分"""
        weights = {
            "competition": 0.25,
            "demand": 0.20,
            "profit": 0.25,
            "ip_risk": 0.20,
            "seasonality": 0.10,
        }
        total = (
            self.competition * weights["competition"]
            + self.demand * weights["demand"]
            + self.profit * weights["profit"]
            + self.ip_risk * weights["ip_risk"]
            + self.seasonality * weights["seasonality"]
        )
        return round(total, 1)

    @property
    def risk_level(self) -> str:
        """综合风险等级"""
        score = self.overall_score
        if score >= 70:
            return "极高"
        elif score >= 50:
            return "高"
        elif score >= 30:
            return "中"
        elif score >= 15:
            return "低"
        else:
            return "极低"

    def to_dict(self) -> dict:
        """转换为字典（适用于前端 Chart.js 雷达图）"""
        return {
            "dimensions": {
                "competition": self.competition,
                "demand": self.demand,
                "profit": self.profit,
                "ip_risk": self.ip_risk,
                "seasonality": self.seasonality,
            },
            "labels": ["竞争风险", "需求风险", "利润风险", "知识产权", "季节性"],
            "values": [
                self.competition,
                self.demand,
                self.profit,
                self.ip_risk,
                self.seasonality,
            ],
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
        }

    def to_chart_data(self) -> dict:
        """生成 Chart.js 兼容的雷达图配置数据"""
        return {
            "type": "radar",
            "data": {
                "labels": ["竞争风险", "需求风险", "利润风险", "知识产权", "季节性"],
                "datasets": [
                    {
                        "label": "风险评分",
                        "data": [
                            self.competition,
                            self.demand,
                            self.profit,
                            self.ip_risk,
                            self.seasonality,
                        ],
                        "backgroundColor": "rgba(255, 99, 132, 0.2)",
                        "borderColor": "rgba(255, 99, 132, 1)",
                        "borderWidth": 2,
                        "pointBackgroundColor": "rgba(255, 99, 132, 1)",
                    }
                ],
            },
            "options": {
                "scales": {
                    "r": {
                        "beginAtZero": True,
                        "max": 100,
                        "ticks": {"stepSize": 20},
                    }
                },
            },
        }


class RiskScoring:
    """
    风险评分引擎

    基于产品数据计算五维风险雷达图，并提供详细的风险分析报告。
    """

    def __init__(self, ai_client=None, ai_model: str = "gpt-4.1-mini"):
        """
        :param ai_client: OpenAI 客户端实例
        :param ai_model: AI 模型名称
        """
        self.risk_analyzer = RiskAnalyzer(ai_client=ai_client, ai_model=ai_model)
        self.ai_client = ai_client

    def calculate_radar(self, product_data: dict) -> FiveDimensionRadar:
        """
        计算产品的五维风险雷达图

        :param product_data: 产品完整数据
        :return: FiveDimensionRadar 实例
        """
        logger.info(f"[RiskScoring] 计算风险雷达: {product_data.get('asin', 'N/A')}")

        competition = self._score_competition(product_data)
        demand = self._score_demand(product_data)
        profit = self._score_profit(product_data)
        ip_risk = self._score_ip_risk(product_data)
        seasonality = self._score_seasonality(product_data)

        radar = FiveDimensionRadar(
            competition=competition,
            demand=demand,
            profit=profit,
            ip_risk=ip_risk,
            seasonality=seasonality,
        )

        logger.info(
            f"[RiskScoring] 雷达计算完成: 综合={radar.overall_score}, "
            f"等级={radar.risk_level}"
        )

        return radar

    def full_risk_report(self, product_data: dict) -> dict:
        """
        生成完整风险报告（包含雷达图 + 详细分析）

        :param product_data: 产品完整数据
        :return: 完整风险报告
        """
        # 五维雷达
        radar = self.calculate_radar(product_data)

        # 详细风险分析
        detailed = self.risk_analyzer.analyze_risks(product_data)

        return {
            "radar": radar.to_dict(),
            "chart_data": radar.to_chart_data(),
            "detailed_analysis": detailed,
            "recommendations": self._generate_recommendations(radar, detailed),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _score_competition(self, data: dict) -> float:
        """评估竞争风险维度"""
        score = 30  # 基础分

        category = data.get("category_analysis", {})
        competition = category.get("competition", {})

        # 竞争等级
        level = competition.get("competition_level", "")
        level_scores = {
            "极高竞争": 40,
            "高竞争": 30,
            "中等竞争": 15,
            "低竞争": 0,
        }
        score += level_scores.get(level, 10)

        # 头部评论数
        top_reviews = competition.get("top_10_avg_reviews", 0)
        if top_reviews > 10000:
            score += 20
        elif top_reviews > 5000:
            score += 15
        elif top_reviews > 1000:
            score += 10
        elif top_reviews > 500:
            score += 5

        # 垄断指数
        monopoly = category.get("monopoly_index", {})
        if monopoly.get("index", 0) > 70:
            score += 15
        elif monopoly.get("index", 0) > 50:
            score += 10

        return min(score, 100)

    def _score_demand(self, data: dict) -> float:
        """评估需求风险维度（需求不足 = 高风险）"""
        score = 20  # 基础分

        category = data.get("category_analysis", {})

        # 市场规模
        market = category.get("market_size", {})
        monthly_revenue = market.get("estimated_monthly_revenue", 0)
        if monthly_revenue < 50000:
            score += 30
        elif monthly_revenue < 200000:
            score += 15
        elif monthly_revenue < 500000:
            score += 5

        # 增长趋势
        trend = category.get("trend", {})
        growth = trend.get("growth_rate", 0)
        if growth < -10:
            score += 25
        elif growth < 0:
            score += 15
        elif growth < 5:
            score += 5

        # BSR 排名（排名越高需求越大，风险越低）
        bsr = data.get("bsr_rank", 0)
        if bsr > 100000:
            score += 20
        elif bsr > 50000:
            score += 10
        elif bsr > 10000:
            score += 5

        return min(score, 100)

    def _score_profit(self, data: dict) -> float:
        """评估利润风险维度"""
        score = 20  # 基础分

        profit_data = data.get("profit", {}).get("profit", {})
        margin = profit_data.get("profit_margin", "0%")

        try:
            margin_val = float(str(margin).replace("%", ""))
        except (ValueError, TypeError):
            margin_val = 0

        if margin_val < 10:
            score += 40
        elif margin_val < 20:
            score += 25
        elif margin_val < 30:
            score += 10
        elif margin_val < 40:
            score += 5

        # ROI
        roi = profit_data.get("roi", "0%")
        try:
            roi_val = float(str(roi).replace("%", ""))
        except (ValueError, TypeError):
            roi_val = 0

        if roi_val < 50:
            score += 20
        elif roi_val < 100:
            score += 10

        # 价格区间风险
        price = data.get("price", 0)
        if price and price < 10:
            score += 15  # 低价品利润空间小
        elif price and price > 100:
            score += 5  # 高价品退货风险

        return min(score, 100)

    def _score_ip_risk(self, data: dict) -> float:
        """评估知识产权风险维度"""
        score = 10  # 基础分

        title = data.get("title", "").lower()
        brand = data.get("brand", "").lower()

        # 品牌关键词检测
        high_risk_brands = [
            "disney", "marvel", "nike", "adidas", "apple", "samsung",
            "pokemon", "hello kitty", "gucci", "louis vuitton", "chanel",
        ]
        for kw in high_risk_brands:
            if kw in title or kw in brand:
                score += 40
                break

        # 有注册品牌
        if brand and brand not in ("unknown", "generic", "unbranded", ""):
            score += 15

        # A+ 内容（品牌保护意识强）
        detail = data.get("detail", {}) or {}
        if detail.get("aplus_images"):
            score += 10

        # 专利关键词
        patent_keywords = ["patented", "patent pending", "proprietary", "exclusive design"]
        for kw in patent_keywords:
            if kw in title:
                score += 20
                break

        return min(score, 100)

    def _score_seasonality(self, data: dict) -> float:
        """评估季节性风险维度"""
        score = 10  # 基础分

        category = data.get("category_analysis", {})
        seasonality = category.get("seasonality", {})

        if seasonality.get("is_seasonal"):
            ratio = seasonality.get("seasonality_ratio", 1)
            if ratio > 5:
                score += 50
            elif ratio > 3:
                score += 35
            elif ratio > 2:
                score += 20
            elif ratio > 1.5:
                score += 10

            # 当前是否在淡季
            low_months = seasonality.get("low_months", [])
            current_month = datetime.now().month
            if current_month in low_months:
                score += 15

        return min(score, 100)

    def _generate_recommendations(
        self, radar: FiveDimensionRadar, detailed: dict
    ) -> list[dict]:
        """
        基于风险分析生成建议

        :param radar: 五维雷达数据
        :param detailed: 详细风险分析
        :return: 建议列表
        """
        recommendations = []

        # 竞争风险建议
        if radar.competition >= 50:
            recommendations.append({
                "dimension": "竞争",
                "risk_level": "高",
                "suggestion": "市场竞争激烈，建议寻找细分市场或差异化切入点",
                "actions": [
                    "分析竞品弱点，找到差异化方向",
                    "考虑长尾关键词策略",
                    "提升 Listing 质量和视觉效果",
                ],
            })

        # 需求风险建议
        if radar.demand >= 50:
            recommendations.append({
                "dimension": "需求",
                "risk_level": "高",
                "suggestion": "市场需求存在不确定性，建议验证后再大量备货",
                "actions": [
                    "小批量测试市场反应",
                    "关注搜索趋势变化",
                    "考虑多平台同步销售分散风险",
                ],
            })

        # 利润风险建议
        if radar.profit >= 50:
            recommendations.append({
                "dimension": "利润",
                "risk_level": "高",
                "suggestion": "利润空间有限，需要严格控制成本",
                "actions": [
                    "优化供应链降低采购成本",
                    "考虑轻小件减少物流费用",
                    "提升转化率降低广告成本",
                ],
            })

        # IP 风险建议
        if radar.ip_risk >= 50:
            recommendations.append({
                "dimension": "知识产权",
                "risk_level": "高",
                "suggestion": "存在知识产权风险，务必进行侵权排查",
                "actions": [
                    "检索相关专利和商标",
                    "避免使用品牌相关关键词",
                    "考虑自主设计和品牌注册",
                ],
            })

        # 季节性风险建议
        if radar.seasonality >= 50:
            recommendations.append({
                "dimension": "季节性",
                "risk_level": "高",
                "suggestion": "产品有明显季节性，需要精确的库存管理",
                "actions": [
                    "旺季前2-3个月开始备货",
                    "淡季减少库存避免长期仓储费",
                    "考虑搭配常青产品平衡收入",
                ],
            })

        if not recommendations:
            recommendations.append({
                "dimension": "综合",
                "risk_level": "低",
                "suggestion": "产品各项风险指标良好，可以考虑推进",
                "actions": [
                    "按计划执行选品流程",
                    "持续监控市场变化",
                    "建立品牌护城河",
                ],
            })

        return recommendations

    def batch_score(self, products: list[dict]) -> list[dict]:
        """
        批量计算产品风险评分

        :param products: 产品列表
        :return: 带风险评分的产品列表
        """
        results = []
        for product in products:
            try:
                radar = self.calculate_radar(product)
                results.append({
                    "asin": product.get("asin", ""),
                    "title": product.get("title", ""),
                    "radar": radar.to_dict(),
                    "overall_risk": radar.overall_score,
                    "risk_level": radar.risk_level,
                })
            except Exception as e:
                logger.error(f"[RiskScoring] 评分失败: {e}")
                results.append({
                    "asin": product.get("asin", ""),
                    "error": str(e),
                })

        # 按风险从低到高排序
        results.sort(key=lambda x: x.get("overall_risk", 100))
        return results
