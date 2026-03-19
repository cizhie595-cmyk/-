"""
跨平台选品系统 - 报告生成模块
功能:
  1. 生成完整的选品分析报告（Markdown格式）
  2. 支持多语言输出（中文/英文/韩文）
  3. 自动检测平台（Coupang / Amazon）并适配数据结构
  4. 包含市场分析、竞品分析、利润分析、风险评估等
"""

import os
import json
from datetime import datetime
from typing import Optional

from utils.logger import get_logger
from i18n import t, get_language

logger = get_logger()


class ReportGenerator:
    """
    选品分析报告生成器
    输出格式: Markdown（可转换为PDF/HTML）
    自动检测平台并适配 Coupang / Amazon 数据结构
    """

    def __init__(self, ai_client=None, platform: str = None):
        """
        :param ai_client: OpenAI 兼容客户端
        :param platform: 平台标识 ("amazon" / "coupang")，为 None 时自动检测
        """
        self.ai_client = ai_client
        self.platform = platform  # 可由外部指定，也可自动检测

    def generate(self, keyword: str, products: list[dict],
                 category_analysis: dict = None,
                 profit_results: list[dict] = None,
                 review_analyses: dict = None,
                 detail_analyses: dict = None,
                 output_dir: str = "reports") -> str:
        """
        生成完整的选品分析报告

        :param keyword: 搜索关键词
        :param products: 筛选后的产品列表
        :param category_analysis: 类目分析结果
        :param profit_results: 利润分析结果
        :param review_analyses: 评论分析结果 {product_id: analysis}
        :param detail_analyses: 详情页分析结果 {product_id: analysis}
        :param output_dir: 输出目录
        :return: 报告文件路径
        """
        logger.info(t("report.generating"))

        lang = get_language()

        # 自动检测平台
        platform = self.platform or self._detect_platform(products, category_analysis)

        report_lines = []

        # === 报告标题 ===
        report_lines.append(self._section_title(keyword, lang, platform))

        # === 1. 市场概况 ===
        report_lines.append(self._section_market_overview(
            keyword, products, category_analysis, lang, platform
        ))

        # === 2. 竞品分析 ===
        report_lines.append(self._section_competitor_analysis(
            products, review_analyses, detail_analyses, lang, platform
        ))

        # === 3. 利润分析 ===
        report_lines.append(self._section_profit_analysis(
            profit_results, lang, platform
        ))

        # === 4. 机会与风险 ===
        report_lines.append(self._section_opportunities_risks(
            category_analysis, lang, platform
        ))

        # === 5. AI 综合建议 ===
        if self.ai_client:
            report_lines.append(self._section_ai_recommendation(
                keyword, category_analysis, profit_results, lang, platform
            ))

        # === 6. 附录 ===
        report_lines.append(self._section_appendix(products, lang, platform))

        # 拼接报告
        report_content = "\n\n".join(report_lines)

        # 保存文件
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{keyword}_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(t("report.saved", path=filepath))
        return filepath

    # ================================================================
    # 平台检测
    # ================================================================

    @staticmethod
    def _detect_platform(products: list[dict], category_analysis: dict = None) -> str:
        """
        根据数据特征自动检测平台。

        Amazon 特征: 产品有 asin 字段，类目分析有 market_size/competition 等
        Coupang 特征: 产品有 coupang_product_id 字段，类目分析有 gmv_estimate 等
        """
        if products:
            sample = products[0]
            if sample.get("asin"):
                return "amazon"
            if sample.get("coupang_product_id"):
                return "coupang"

        if category_analysis:
            if "market_size" in category_analysis:
                return "amazon"
            if "gmv_estimate" in category_analysis:
                return "coupang"

        return "coupang"  # 默认

    # ================================================================
    # 报告标题
    # ================================================================

    def _section_title(self, keyword: str, lang: str, platform: str) -> str:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        if platform == "amazon":
            titles = {
                "zh_CN": f"# Amazon 选品分析报告：{keyword}\n\n> 生成时间：{now}\n> 系统版本：Amazon Visionary Sourcing Tool v2.0",
                "en_US": f"# Amazon Product Selection Report: {keyword}\n\n> Generated: {now}\n> System: Amazon Visionary Sourcing Tool v2.0",
                "ko_KR": f"# 아마존 상품 선정 분석 보고서: {keyword}\n\n> 생성 시간: {now}\n> 시스템: Amazon Visionary Sourcing Tool v2.0",
            }
        else:
            titles = {
                "zh_CN": f"# Coupang 选品分析报告：{keyword}\n\n> 生成时间：{now}\n> 系统版本：Coupang Product Selection System v1.0",
                "en_US": f"# Coupang Product Selection Report: {keyword}\n\n> Generated: {now}\n> System: Coupang Product Selection System v1.0",
                "ko_KR": f"# 쿠팡 상품 선정 분석 보고서: {keyword}\n\n> 생성 시간: {now}\n> 시스템: Coupang Product Selection System v1.0",
            }

        return titles.get(lang, titles["zh_CN"])

    # ================================================================
    # 市场概况
    # ================================================================

    def _section_market_overview(self, keyword: str, products: list,
                                  category: dict, lang: str, platform: str) -> str:
        headers = {"zh_CN": "## 一、市场概况", "en_US": "## 1. Market Overview", "ko_KR": "## 1. 시장 개요"}
        lines = [headers.get(lang, headers["zh_CN"])]

        if not category:
            lines.append(f"\n{'暂无类目分析数据' if lang == 'zh_CN' else 'No category analysis data available'}")
            return "\n".join(lines)

        if platform == "amazon":
            lines.extend(self._market_overview_amazon(category, lang))
        else:
            lines.extend(self._market_overview_coupang(category, lang))

        return "\n".join(lines)

    def _market_overview_amazon(self, category: dict, lang: str) -> list[str]:
        """Amazon 平台市场概况 - 适配 AmazonCategoryAnalyzer 输出"""
        lines = []

        # 市场容量 (market_size)
        market = category.get("market_size", {})
        if market:
            total_gmv = market.get("estimated_total_monthly_gmv", 0)
            tier = market.get("market_size_tier", "")
            avg_sales = market.get("avg_monthly_sales_per_product", 0)
            avg_price = market.get("avg_price", 0)

            lbl = "月度 GMV 预估" if lang == "zh_CN" else "Monthly GMV Estimate"
            lines.append(f"\n**{lbl}**: ${total_gmv:,.0f}")
            if tier:
                lines.append(f"- {'市场规模' if lang == 'zh_CN' else 'Market Size'}: {tier}")
            if avg_sales:
                lines.append(f"- {'平均月销量' if lang == 'zh_CN' else 'Avg Monthly Sales'}: {avg_sales:,}")
            if avg_price:
                lines.append(f"- {'平均售价' if lang == 'zh_CN' else 'Avg Price'}: ${avg_price:.2f}")

        # 竞争格局 (competition)
        comp = category.get("competition", {})
        if comp:
            level = comp.get("competition_level", "")
            difficulty = comp.get("new_entry_difficulty", "")
            avg_reviews = comp.get("avg_review_count", 0)
            top10_reviews = comp.get("top_10_avg_reviews", 0)

            lbl = "竞争格局" if lang == "zh_CN" else "Competition"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"\n| {'指标' if lang == 'zh_CN' else 'Metric'} | {'值' if lang == 'zh_CN' else 'Value'} |")
            lines.append("|---|---|")
            if level:
                lines.append(f"| {'竞争强度' if lang == 'zh_CN' else 'Level'} | {level} |")
            if difficulty:
                lines.append(f"| {'进入难度' if lang == 'zh_CN' else 'Entry Difficulty'} | {difficulty} |")
            lines.append(f"| {'平均评论数' if lang == 'zh_CN' else 'Avg Reviews'} | {avg_reviews:,} |")
            lines.append(f"| {'Top10 平均评论' if lang == 'zh_CN' else 'Top10 Avg Reviews'} | {top10_reviews:,} |")
            lines.append(f"| {'平均评分' if lang == 'zh_CN' else 'Avg Rating'} | {comp.get('avg_rating', 0)} |")

        # 价格分析 (pricing)
        pricing = category.get("pricing", {})
        if pricing:
            lbl = "价格分布" if lang == "zh_CN" else "Price Distribution"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"\n| {'指标' if lang == 'zh_CN' else 'Metric'} | {'值 (USD)' if lang == 'zh_CN' else 'Value (USD)'} |")
            lines.append("|---|---|")
            for key, label_zh, label_en in [
                ("min_price", "最低价", "Min"),
                ("max_price", "最高价", "Max"),
                ("avg_price", "均价", "Average"),
                ("median_price", "中位数", "Median"),
            ]:
                val = pricing.get(key, 0)
                if val:
                    lbl_col = label_zh if lang == "zh_CN" else label_en
                    lines.append(f"| {lbl_col} | ${val:.2f} |")

            # 价格区间分布
            buckets = pricing.get("price_buckets", {})
            if buckets:
                lbl = "价格区间分布" if lang == "zh_CN" else "Price Range Distribution"
                lines.append(f"\n**{lbl}**:")
                for bucket, count in buckets.items():
                    lines.append(f"- {bucket}: {count}")

        # 品牌集中度 (brand_concentration)
        brand = category.get("brand_concentration", {})
        if brand:
            lbl = "品牌集中度" if lang == "zh_CN" else "Brand Concentration"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"- HHI {'指数' if lang == 'zh_CN' else 'Index'}: {brand.get('hhi_index', 0)}")
            lines.append(f"- {'集中度' if lang == 'zh_CN' else 'Level'}: {brand.get('concentration_level', '')}")
            lines.append(f"- Top3 {'市场份额' if lang == 'zh_CN' else 'Share'}: {brand.get('top_3_share', '')}")

            top_brands = brand.get("top_brands", [])[:5]
            if top_brands:
                lbl = "头部品牌" if lang == "zh_CN" else "Top Brands"
                lines.append(f"\n**{lbl}**:")
                for b in top_brands:
                    lines.append(f"- {b.get('brand', 'N/A')}: {b.get('share', '')} ({b.get('count', 0)})")

        # 垄断度 (monopoly_index)
        monopoly = category.get("monopoly_index", {})
        if monopoly:
            lbl = "垄断度评估" if lang == "zh_CN" else "Monopoly Assessment"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"- {'垄断指数' if lang == 'zh_CN' else 'Index'}: {monopoly.get('index', 0)}")
            lines.append(f"- {'等级' if lang == 'zh_CN' else 'Level'}: {monopoly.get('level', '')}")
            lines.append(f"- {'建议' if lang == 'zh_CN' else 'Advice'}: {monopoly.get('advice', '')}")

        # 物流方式分布 (fulfillment_distribution)
        fulfillment = category.get("fulfillment_distribution", {})
        if fulfillment:
            lbl = "物流方式分布" if lang == "zh_CN" else "Fulfillment Distribution"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"- FBA: {fulfillment.get('fba_percentage', 0)}% ({fulfillment.get('fba_count', 0)})")
            lines.append(f"- FBM: {fulfillment.get('fbm_percentage', 0)}% ({fulfillment.get('fbm_count', 0)})")
            rec = fulfillment.get("recommendation", "")
            if rec:
                lines.append(f"- {'推荐' if lang == 'zh_CN' else 'Recommended'}: {rec}")

        return lines

    def _market_overview_coupang(self, category: dict, lang: str) -> list[str]:
        """Coupang 平台市场概况 - 保持原有逻辑"""
        lines = []

        # GMV
        gmv = category.get("gmv_estimate", {})
        if gmv:
            monthly_gmv = gmv.get("monthly_gmv_krw", 0)
            lbl = "月度GMV预估" if lang == "zh_CN" else "Monthly GMV Estimate" if lang == "en_US" else "월 GMV 추정"
            lines.append(f"\n**{lbl}**: {monthly_gmv:,.0f} KRW")

        # 垄断程度
        monopoly = category.get("monopoly_analysis", {})
        if monopoly.get("available"):
            lbl = "垄断程度" if lang == "zh_CN" else "Monopoly Level" if lang == "en_US" else "독점 수준"
            lines.append(f"\n**{lbl}**: {monopoly.get('description', '')}")
            lines.append(f"- Top1 占比: {monopoly.get('top1_ratio', 0) * 100:.1f}%")
            lines.append(f"- Top3 占比: {monopoly.get('top3_ratio', 0) * 100:.1f}%")
            lines.append(f"- Top10 占比: {monopoly.get('top10_ratio', 0) * 100:.1f}%")

        # 新品占比
        new_prod = category.get("new_product_analysis", {})
        if new_prod:
            lbl = "新品占比" if lang == "zh_CN" else "New Product Ratio" if lang == "en_US" else "신제품 비율"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"- 3个月内新品: {new_prod.get('new_3m_count', 0)} ({new_prod.get('new_3m_ratio', 0) * 100:.1f}%)")
            lines.append(f"- 市场成熟度: {new_prod.get('market_maturity', 'unknown')}")

        # 价格分布
        price = category.get("price_distribution", {})
        if price.get("available"):
            lbl = "价格分布" if lang == "zh_CN" else "Price Distribution" if lang == "en_US" else "가격 분포"
            lines.append(f"\n**{lbl}**:")
            lines.append(f"\n| {'指标' if lang == 'zh_CN' else 'Metric'} | {'值 (KRW)' if lang == 'zh_CN' else 'Value (KRW)'} |")
            lines.append("|---|---|")
            lines.append(f"| {'最低价' if lang == 'zh_CN' else 'Min'} | {price.get('min', 0):,.0f} |")
            lines.append(f"| {'最高价' if lang == 'zh_CN' else 'Max'} | {price.get('max', 0):,.0f} |")
            lines.append(f"| {'均价' if lang == 'zh_CN' else 'Average'} | {price.get('avg', 0):,.0f} |")
            lines.append(f"| {'中位数' if lang == 'zh_CN' else 'Median'} | {price.get('median', 0):,.0f} |")

        return lines

    # ================================================================
    # 竞品分析
    # ================================================================

    def _section_competitor_analysis(self, products: list, reviews: dict,
                                      details: dict, lang: str, platform: str) -> str:
        headers = {"zh_CN": "## 二、竞品分析", "en_US": "## 2. Competitor Analysis", "ko_KR": "## 2. 경쟁 분석"}
        lines = [headers.get(lang, headers["zh_CN"])]

        # 产品列表表格
        lbl = "Top 产品列表" if lang == "zh_CN" else "Top Products" if lang == "en_US" else "상위 제품 목록"
        lines.append(f"\n### {lbl}")

        if platform == "amazon":
            lines.extend(self._competitor_table_amazon(products, lang))
        else:
            lines.extend(self._competitor_table_coupang(products, lang))

        # 评论分析摘要（通用）
        if reviews:
            lbl = "评论分析摘要" if lang == "zh_CN" else "Review Analysis Summary" if lang == "en_US" else "리뷰 분석 요약"
            lines.append(f"\n### {lbl}")
            for pid, analysis in list(reviews.items())[:5]:
                selling = analysis.get("selling_points", [])[:3]
                pain = analysis.get("pain_points", [])[:3]
                if selling:
                    sp_text = ", ".join([
                        s.get("point", "") if isinstance(s, dict) else str(s)
                        for s in selling
                    ])
                    lines.append(f"\n**{pid}** - {'卖点' if lang == 'zh_CN' else 'Selling Points'}: {sp_text}")
                if pain:
                    pp_text = ", ".join([
                        p.get("point", "") if isinstance(p, dict) else str(p)
                        for p in pain
                    ])
                    lines.append(f"**{pid}** - {'痛点' if lang == 'zh_CN' else 'Pain Points'}: {pp_text}")

        return "\n".join(lines)

    def _competitor_table_amazon(self, products: list, lang: str) -> list[str]:
        """Amazon 竞品表格 - 使用 ASIN、BSR、FBA/FBM"""
        lines = []
        h = {
            "zh_CN": "| # | ASIN | 产品名称 | 价格(USD) | 评分 | 评论数 | BSR | 物流 |",
            "en_US": "| # | ASIN | Product | Price(USD) | Rating | Reviews | BSR | Fulfillment |",
        }
        lines.append(f"\n{h.get(lang, h['zh_CN'])}")
        lines.append("|---|------|---|---|---|---|---|---|")

        for i, p in enumerate(products[:20]):
            title = p.get("title", "")[:30]
            price = p.get("price", 0) or p.get("price_current", 0) or 0
            price_str = f"${price:.2f}" if price else "N/A"
            rating = p.get("rating", "N/A")
            review_count = p.get("review_count", 0)
            asin = p.get("asin", "N/A")
            bsr = p.get("bsr", 0) or p.get("bsr_rank", 0) or ""
            fulfillment = (
                p.get("fulfillment_type", "")
                or p.get("fulfillment", "")
                or "N/A"
            )
            lines.append(f"| {i + 1} | {asin} | {title} | {price_str} | {rating} | {review_count} | {bsr} | {fulfillment} |")

        return lines

    def _competitor_table_coupang(self, products: list, lang: str) -> list[str]:
        """Coupang 竞品表格 - 使用价格(KRW)、配送类型"""
        lines = []
        h = {
            "zh_CN": "| # | 产品名称 | 价格 | 评分 | 评论数 | 配送 |",
            "en_US": "| # | Product | Price | Rating | Reviews | Delivery |",
        }
        lines.append(f"\n{h.get(lang, h['zh_CN'])}")
        lines.append("|---|---|---|---|---|---|")

        for i, p in enumerate(products[:20]):
            title = p.get("title", "")[:30]
            price = f"{p.get('price', 0):,.0f}" if p.get("price") else "N/A"
            rating = p.get("rating", "N/A")
            review_count = p.get("review_count", 0)
            delivery = p.get("delivery_type", "unknown")
            lines.append(f"| {i + 1} | {title} | {price} | {rating} | {review_count} | {delivery} |")

        return lines

    # ================================================================
    # 利润分析
    # ================================================================

    def _section_profit_analysis(self, profit_results: list, lang: str, platform: str) -> str:
        headers = {"zh_CN": "## 三、利润分析", "en_US": "## 3. Profit Analysis", "ko_KR": "## 3. 수익 분석"}
        lines = [headers.get(lang, headers["zh_CN"])]

        if not profit_results:
            lines.append(f"\n{'暂无利润数据' if lang == 'zh_CN' else 'No profit data available'}")
            return "\n".join(lines)

        if platform == "amazon":
            lines.extend(self._profit_table_amazon(profit_results, lang))
        else:
            lines.extend(self._profit_table_coupang(profit_results, lang))

        return "\n".join(lines)

    def _profit_table_amazon(self, profit_results: list, lang: str) -> list[str]:
        """Amazon FBA 利润表格 - 适配 AmazonFBAProfitCalculator 输出"""
        lines = []
        h = {
            "zh_CN": "| ASIN | 售价(USD) | 采购价(RMB) | FBA费 | 推荐费 | 利润(USD) | 利润率 | ROI |",
            "en_US": "| ASIN | Price(USD) | COGS(RMB) | FBA Fee | Referral | Profit(USD) | Margin | ROI |",
        }
        lines.append(f"\n{h.get(lang, h['zh_CN'])}")
        lines.append("|---|---|---|---|---|---|---|---|")

        for r in profit_results[:10]:
            # AmazonFBAProfitCalculator 输出嵌套结构
            costs = r.get("costs", {})
            profit = r.get("profit", {})
            asin = r.get("asin", "N/A")
            selling_price = r.get("selling_price", 0)
            cogs_rmb = costs.get("cogs_rmb", 0)
            fba_fee = costs.get("fba_fulfillment_fee", 0)
            referral_fee = costs.get("referral_fee", 0)
            profit_usd = profit.get("profit_per_unit_usd", 0)
            margin = profit.get("profit_margin", "N/A")
            roi = profit.get("roi", "N/A")

            lines.append(
                f"| {asin} "
                f"| ${selling_price:.2f} "
                f"| ¥{cogs_rmb:.2f} "
                f"| ${fba_fee:.2f} "
                f"| ${referral_fee:.2f} "
                f"| ${profit_usd:.2f} "
                f"| {margin} "
                f"| {roi} |"
            )

        # 利润健康度摘要
        healthy = [r for r in profit_results if r.get("health_check", {}).get("is_healthy")]
        if profit_results:
            lbl = "利润健康度" if lang == "zh_CN" else "Profit Health"
            lines.append(f"\n**{lbl}**: {len(healthy)}/{len(profit_results[:10])} "
                         f"{'个方案达标' if lang == 'zh_CN' else 'plans meet threshold'}")

        return lines

    def _profit_table_coupang(self, profit_results: list, lang: str) -> list[str]:
        """Coupang 利润表格 - 保持原有逻辑"""
        lines = []
        h = {
            "zh_CN": "| 货源 | 采购价(RMB) | 售价(KRW) | 利润(KRW) | 利润率 | ROI |",
            "en_US": "| Source | Cost(RMB) | Price(KRW) | Profit(KRW) | Margin | ROI |",
        }
        lines.append(f"\n{h.get(lang, h['zh_CN'])}")
        lines.append("|---|---|---|---|---|---|")

        for r in profit_results[:10]:
            source = r.get("source", {})
            lines.append(
                f"| {source.get('supplier_name', 'N/A')[:15]} "
                f"| {source.get('price_rmb', 0):.2f} "
                f"| {r.get('selling_price_krw', 0):,.0f} "
                f"| {r.get('profit_per_unit_krw', 0):,.0f} "
                f"| {r.get('profit_margin', 'N/A')} "
                f"| {r.get('roi', 'N/A')} |"
            )

        return lines

    # ================================================================
    # 机会与风险
    # ================================================================

    def _section_opportunities_risks(self, category: dict, lang: str, platform: str) -> str:
        headers = {"zh_CN": "## 四、机会与风险", "en_US": "## 4. Opportunities & Risks", "ko_KR": "## 4. 기회와 위험"}
        lines = [headers.get(lang, headers["zh_CN"])]

        if not category:
            lines.append(f"\n{'暂无数据' if lang == 'zh_CN' else 'No data available'}")
            return "\n".join(lines)

        if platform == "amazon":
            lines.extend(self._opportunities_amazon(category, lang))
        else:
            lines.extend(self._opportunities_coupang(category, lang))

        return "\n".join(lines)

    def _opportunities_amazon(self, category: dict, lang: str) -> list[str]:
        """Amazon 机会与风险 - 适配 AmazonCategoryAnalyzer 的 opportunity 字段"""
        lines = []

        opportunity = category.get("opportunity", {})
        if opportunity:
            score = opportunity.get("opportunity_score", 0)
            grade = opportunity.get("grade", "")
            rec = opportunity.get("recommendation", "")

            lbl = "综合评估" if lang == "zh_CN" else "Overall Assessment"
            lines.append(f"\n**{lbl}**: {rec} (Grade: {grade}, Score: {score}/100)")

            # 机会
            opps = opportunity.get("opportunities", [])
            if opps:
                lbl = "市场机会" if lang == "zh_CN" else "Opportunities"
                lines.append(f"\n### {lbl}")
                for i, opp in enumerate(opps):
                    lines.append(f"{i + 1}. {opp}")

            # 风险
            risks = opportunity.get("risk_factors", [])
            if risks:
                lbl = "风险提示" if lang == "zh_CN" else "Risk Factors"
                lines.append(f"\n### {lbl}")
                for i, risk in enumerate(risks):
                    lines.append(f"{i + 1}. {risk}")

        # AI 总结
        ai_summary = category.get("ai_summary", "")
        if ai_summary:
            lbl = "AI 市场分析" if lang == "zh_CN" else "AI Market Analysis"
            lines.append(f"\n### {lbl}")
            lines.append(ai_summary)

        return lines

    def _opportunities_coupang(self, category: dict, lang: str) -> list[str]:
        """Coupang 机会与风险 - 保持原有 ai_assessment 逻辑"""
        lines = []

        ai_assess = category.get("ai_assessment", {})
        if ai_assess:
            opps = ai_assess.get("opportunities", [])
            if opps:
                lbl = "市场机会" if lang == "zh_CN" else "Opportunities" if lang == "en_US" else "시장 기회"
                lines.append(f"\n### {lbl}")
                for i, opp in enumerate(opps):
                    lines.append(f"{i + 1}. {opp}")

            risks = ai_assess.get("risks", [])
            if risks:
                lbl = "风险提示" if lang == "zh_CN" else "Risks" if lang == "en_US" else "위험 요소"
                lines.append(f"\n### {lbl}")
                for i, risk in enumerate(risks):
                    lines.append(f"{i + 1}. {risk}")

            strategy = ai_assess.get("entry_strategy", "")
            if strategy:
                lbl = "建议进入策略" if lang == "zh_CN" else "Entry Strategy" if lang == "en_US" else "진입 전략"
                lines.append(f"\n### {lbl}")
                lines.append(strategy)

        return lines

    # ================================================================
    # AI 综合建议
    # ================================================================

    def _section_ai_recommendation(self, keyword: str, category: dict,
                                    profit: list, lang: str, platform: str) -> str:
        headers = {"zh_CN": "## 五、AI 综合建议", "en_US": "## 5. AI Recommendation", "ko_KR": "## 5. AI 종합 권고"}
        lines = [headers.get(lang, headers["zh_CN"])]

        output_lang = {"zh_CN": "Chinese", "en_US": "English", "ko_KR": "Korean"}.get(lang, "Chinese")
        platform_name = "Amazon" if platform == "amazon" else "Coupang"

        prompt = f"""Based on the following {platform_name} market analysis for keyword "{keyword}", provide a final recommendation.

Category Analysis: {json.dumps(category or {}, ensure_ascii=False, default=str)[:2000]}
Profit Analysis: {json.dumps(profit[:3] if profit else [], ensure_ascii=False, default=str)[:1000]}

Provide:
1. Overall recommendation (ENTER / CAUTIOUS / AVOID)
2. 3-5 key action items if entering this market
3. Estimated monthly profit potential
4. Key success factors

Respond in {output_lang} as plain text (not JSON)."""

        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500,
            )
            lines.append(f"\n{response.choices[0].message.content.strip()}")
        except Exception as e:
            logger.error(f"AI recommendation error: {e}")
            lines.append(f"\n{'AI建议生成失败' if lang == 'zh_CN' else 'AI recommendation generation failed'}")

        return "\n".join(lines)

    # ================================================================
    # 附录
    # ================================================================

    def _section_appendix(self, products: list, lang: str, platform: str) -> str:
        headers = {"zh_CN": "## 附录", "en_US": "## Appendix", "ko_KR": "## 부록"}
        lines = [headers.get(lang, headers["zh_CN"])]

        lines.append(f"\n{'分析产品总数' if lang == 'zh_CN' else 'Total Products Analyzed'}: {len(products)}")
        lines.append(f"{'报告生成时间' if lang == 'zh_CN' else 'Report Generated'}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"{'分析平台' if lang == 'zh_CN' else 'Platform'}: {platform.capitalize()}")

        platform_name = "Amazon Visionary Sourcing Tool" if platform == "amazon" else "Coupang 选品系统"
        lines.append(f"\n---\n*{'本报告由 ' + platform_name + ' 自动生成' if lang == 'zh_CN' else 'This report was auto-generated by ' + platform_name}*")

        return "\n".join(lines)
