"""
第三方服务商推荐引擎 (PRD 5.3 BIZ-05)

在风险报告和分析结果中，根据产品风险维度智能推荐相关第三方服务商，
并通过返佣链接实现商业化。

推荐场景：
  - 知识产权风险高 → 推荐 Trademarkia（商标查询）
  - 物流需求 → 推荐 Deliverr（跨境物流）
  - 竞争激烈 → 推荐 Helium 10 / Jungle Scout（分析工具）
  - Listing 优化 → 推荐 Canva（设计工具）
  - 合规需求 → 推荐 SGS（质检认证）
"""

from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 服务商数据库
# ============================================================

SERVICE_CATALOG = {
    "trademarkia": {
        "name": "Trademarkia",
        "category": "ip_protection",
        "icon": "shield-check",
        "color": "#6366f1",
        "tagline": "商标查询与注册",
        "description": "全球商标数据库搜索，快速检查品牌名称是否已被注册，避免侵权风险。",
        "features": ["全球商标搜索", "商标注册申请", "侵权监控", "法律咨询"],
        "pricing": "搜索免费，注册 $199 起",
        "url": "https://www.trademarkia.com",
        "cta_text": "免费查询商标",
        "cta_path": "/search",
        "trigger_dimension": "ip_risk",
        "trigger_threshold": 40,
    },
    "deliverr": {
        "name": "Deliverr",
        "category": "logistics",
        "icon": "truck",
        "color": "#0ea5e9",
        "tagline": "跨境物流与弹性仓储",
        "description": "智能分仓系统，2 天送达覆盖全美，支持 FBA 补货和多渠道履约。",
        "features": ["智能分仓", "2 天送达", "FBA 补货", "多渠道履约"],
        "pricing": "按件计费，$3.99 起",
        "url": "https://www.deliverr.com",
        "cta_text": "获取报价",
        "cta_path": "/pricing",
        "trigger_dimension": "seasonality",
        "trigger_threshold": 50,
    },
    "helium10": {
        "name": "Helium 10",
        "category": "analytics",
        "icon": "chart-bar",
        "color": "#f59e0b",
        "tagline": "Amazon 卖家工具套件",
        "description": "一站式 Amazon 卖家工具，包含选品、关键词研究、Listing 优化、利润追踪等。",
        "features": ["Black Box 选品", "Cerebro 关键词", "Listing 优化", "利润追踪"],
        "pricing": "$29/月起",
        "url": "https://www.helium10.com",
        "cta_text": "免费试用",
        "cta_path": "/pricing",
        "trigger_dimension": "competition",
        "trigger_threshold": 50,
    },
    "junglescout": {
        "name": "Jungle Scout",
        "category": "analytics",
        "icon": "magnifying-glass-chart",
        "color": "#22c55e",
        "tagline": "Amazon 选品与市场分析",
        "description": "精准的销量估算和市场趋势分析，帮助发现高潜力低竞争的产品机会。",
        "features": ["产品追踪器", "关键词侦查", "销量估算", "供应商数据库"],
        "pricing": "$49/月起",
        "url": "https://www.junglescout.com",
        "cta_text": "开始分析",
        "cta_path": "/pricing",
        "trigger_dimension": "competition",
        "trigger_threshold": 45,
    },
    "canva": {
        "name": "Canva Pro",
        "category": "design",
        "icon": "paint-brush",
        "color": "#8b5cf6",
        "tagline": "产品图片与 A+ 页面设计",
        "description": "专业级设计工具，提供 Amazon 产品图片模板、A+ 页面模板和品牌素材。",
        "features": ["产品图片模板", "A+ 页面设计", "品牌 Kit", "AI 抠图"],
        "pricing": "$12.99/月",
        "url": "https://www.canva.com",
        "cta_text": "免费开始设计",
        "cta_path": "/pro",
        "trigger_dimension": None,
        "trigger_threshold": 0,
    },
    "sgs": {
        "name": "SGS",
        "category": "compliance",
        "icon": "clipboard-check",
        "color": "#ef4444",
        "tagline": "产品质检与认证",
        "description": "全球领先的检验认证机构，提供产品质量检测、合规认证和供应商审核服务。",
        "features": ["产品质检", "CE/FCC 认证", "供应商审核", "验货服务"],
        "pricing": "按项目报价",
        "url": "https://www.sgs.com",
        "cta_text": "获取报价",
        "cta_path": "/en/consumer-goods-retail",
        "trigger_dimension": "ip_risk",
        "trigger_threshold": 30,
    },
}


class ServiceRecommendationEngine:
    """
    第三方服务商推荐引擎

    根据产品分析结果和风险维度，智能推荐相关的第三方服务商，
    生成带返佣链接的推荐卡片数据。
    """

    def __init__(self, affiliate_manager=None):
        """
        :param affiliate_manager: AffiliateManager 实例（用于生成返佣链接）
        """
        self.affiliate_manager = affiliate_manager
        self.catalog = SERVICE_CATALOG.copy()

    def get_recommendations(self, risk_dimensions: dict = None,
                             analysis_context: dict = None,
                             max_count: int = 4) -> list[dict]:
        """
        根据风险维度和分析上下文生成推荐列表。

        :param risk_dimensions: 风险维度分数 {competition, demand, profit, ip_risk, seasonality}
        :param analysis_context: 分析上下文 {category, price_range, marketplace, ...}
        :param max_count: 最大推荐数量
        :return: 推荐卡片数据列表
        """
        scored_services = []

        for service_id, config in self.catalog.items():
            score = self._calculate_relevance_score(
                config, risk_dimensions, analysis_context
            )
            card = self._build_card(service_id, config, score, risk_dimensions)
            scored_services.append(card)

        # 按相关性分数排序
        scored_services.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scored_services[:max_count]

    def get_contextual_recommendations(self, report_data: dict,
                                         max_count: int = 3) -> list[dict]:
        """
        从综合报告数据中提取风险维度，生成上下文相关的推荐。

        :param report_data: 综合报告数据
        :param max_count: 最大推荐数量
        :return: 推荐卡片数据列表
        """
        # 从报告中提取风险维度
        risk_dimensions = {}
        if report_data.get("risk_analysis"):
            risk = report_data["risk_analysis"]
            risk_dimensions = {
                "competition": risk.get("competition_score", 50),
                "demand": risk.get("demand_score", 50),
                "profit": risk.get("profit_score", 50),
                "ip_risk": risk.get("ip_risk_score", 30),
                "seasonality": risk.get("seasonality_score", 30),
            }

        # 从报告中提取分析上下文
        analysis_context = {
            "category": report_data.get("category", ""),
            "marketplace": report_data.get("marketplace", "US"),
            "price_range": report_data.get("avg_price", 0),
            "has_brand_risk": risk_dimensions.get("ip_risk", 0) >= 40,
        }

        return self.get_recommendations(risk_dimensions, analysis_context, max_count)

    def get_service_by_id(self, service_id: str) -> dict:
        """获取单个服务商的完整信息"""
        config = self.catalog.get(service_id)
        if not config:
            return None
        return self._build_card(service_id, config, 50)

    def get_all_services(self) -> list[dict]:
        """获取所有服务商列表"""
        return [
            self._build_card(sid, config, 50)
            for sid, config in self.catalog.items()
        ]

    def render_recommendation_cards_html(self, recommendations: list[dict]) -> str:
        """
        将推荐列表渲染为 HTML 卡片组件。

        :param recommendations: 推荐卡片数据列表
        :return: HTML 字符串
        """
        if not recommendations:
            return ""

        cards_html = []
        for rec in recommendations:
            relevance_badge = ""
            if rec["relevance"] == "high":
                relevance_badge = '<span class="badge badge-danger">强烈推荐</span>'
            elif rec["relevance"] == "medium":
                relevance_badge = '<span class="badge badge-warning">推荐</span>'

            reason_html = ""
            if rec.get("reason"):
                reason_html = f'<p class="service-reason">{rec["reason"]}</p>'

            features_html = " ".join(
                f'<span class="feature-tag">{f}</span>'
                for f in rec.get("features", [])[:4]
            )

            card = f"""
            <div class="service-card" style="border-left: 4px solid {rec['color']}">
                <div class="service-header">
                    <div class="service-icon" style="background: {rec['color']}20; color: {rec['color']}">
                        <i class="icon-{rec['icon']}"></i>
                    </div>
                    <div class="service-info">
                        <h4>{rec['name']} {relevance_badge}</h4>
                        <p class="service-tagline">{rec['tagline']}</p>
                    </div>
                </div>
                <p class="service-desc">{rec['description']}</p>
                {reason_html}
                <div class="service-features">{features_html}</div>
                <div class="service-footer">
                    <span class="service-pricing">{rec['pricing']}</span>
                    <a href="{rec['url']}" target="_blank" rel="noopener"
                       class="btn btn-sm" style="background: {rec['color']}; color: white;"
                       onclick="trackServiceClick('{rec['service_id']}')">
                        {rec['cta_text']}
                    </a>
                </div>
            </div>
            """
            cards_html.append(card)

        return f"""
        <div class="service-recommendations">
            <h3 class="section-title">推荐工具与服务</h3>
            <p class="section-desc">根据分析结果，以下工具可以帮助您降低风险、提升竞争力</p>
            <div class="service-grid">
                {"".join(cards_html)}
            </div>
        </div>
        """

    # ============================================================
    # 内部方法
    # ============================================================

    def _calculate_relevance_score(self, config: dict,
                                     risk_dimensions: dict = None,
                                     analysis_context: dict = None) -> float:
        """计算服务商与当前分析场景的相关性分数 (0-100)"""
        score = 30.0  # 基础分

        if not risk_dimensions:
            return score

        trigger_dim = config.get("trigger_dimension")
        trigger_threshold = config.get("trigger_threshold", 50)

        if trigger_dim and trigger_dim in risk_dimensions:
            dim_value = risk_dimensions[trigger_dim]
            if dim_value >= trigger_threshold:
                # 超过阈值，大幅提升分数
                excess = dim_value - trigger_threshold
                score += 40 + min(excess, 30)
            else:
                # 未超过阈值，轻微提升
                score += (dim_value / trigger_threshold) * 20

        # 上下文加分
        if analysis_context:
            if config["category"] == "ip_protection" and analysis_context.get("has_brand_risk"):
                score += 15
            if config["category"] == "logistics" and analysis_context.get("marketplace") in ("US", "UK", "DE"):
                score += 10

        return min(score, 100)

    def _build_card(self, service_id: str, config: dict,
                      relevance_score: float,
                      risk_dimensions: dict = None) -> dict:
        """构建推荐卡片数据"""
        # 确定相关性等级
        if relevance_score >= 70:
            relevance = "high"
        elif relevance_score >= 45:
            relevance = "medium"
        else:
            relevance = "low"

        # 生成推荐理由
        reason = self._generate_reason(config, risk_dimensions)

        # 生成返佣链接
        url = config["url"] + config.get("cta_path", "")
        if self.affiliate_manager:
            url = self.affiliate_manager.generate_service_link(
                service_id, config.get("cta_path", "")
            )

        return {
            "service_id": service_id,
            "name": config["name"],
            "category": config["category"],
            "icon": config["icon"],
            "color": config["color"],
            "tagline": config["tagline"],
            "description": config["description"],
            "features": config["features"],
            "pricing": config["pricing"],
            "url": url,
            "cta_text": config["cta_text"],
            "relevance": relevance,
            "relevance_score": relevance_score,
            "reason": reason,
        }

    @staticmethod
    def _generate_reason(config: dict, risk_dimensions: dict = None) -> str:
        """根据风险维度生成推荐理由"""
        if not risk_dimensions:
            return ""

        trigger_dim = config.get("trigger_dimension")
        if not trigger_dim or trigger_dim not in risk_dimensions:
            return ""

        dim_value = risk_dimensions[trigger_dim]
        threshold = config.get("trigger_threshold", 50)

        if dim_value < threshold:
            return ""

        reasons = {
            "ip_risk": f"知识产权风险评分 {dim_value}/100，建议提前进行商标和专利排查",
            "competition": f"市场竞争度 {dim_value}/100，建议使用专业工具深入分析竞品策略",
            "seasonality": f"季节性波动评分 {dim_value}/100，建议使用弹性仓储应对需求变化",
            "demand": f"需求不确定性 {dim_value}/100，建议深入验证市场需求",
            "profit": f"利润风险评分 {dim_value}/100，建议优化成本结构",
        }

        return reasons.get(trigger_dim, "")
