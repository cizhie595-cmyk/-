"""
Coupang 选品系统 - 报告生成模块
功能:
  1. 生成完整的选品分析报告（Markdown格式）
  2. 支持多语言输出（中文/英文/韩文）
  3. 包含市场分析、利润分析、风险评估等
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
    """

    def __init__(self, ai_client=None):
        self.ai_client = ai_client

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
        report_lines = []

        # === 报告标题 ===
        report_lines.append(self._section_title(keyword, lang))

        # === 1. 市场概况 ===
        report_lines.append(self._section_market_overview(keyword, products, category_analysis, lang))

        # === 2. 竞品分析 ===
        report_lines.append(self._section_competitor_analysis(products, review_analyses, detail_analyses, lang))

        # === 3. 利润分析 ===
        report_lines.append(self._section_profit_analysis(profit_results, lang))

        # === 4. 机会与风险 ===
        report_lines.append(self._section_opportunities_risks(category_analysis, lang))

        # === 5. AI 综合建议 ===
        if self.ai_client:
            report_lines.append(self._section_ai_recommendation(keyword, category_analysis, profit_results, lang))

        # === 6. 附录 ===
        report_lines.append(self._section_appendix(products, lang))

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

    def _section_title(self, keyword: str, lang: str) -> str:
        titles = {
            "zh_CN": f"# Coupang 选品分析报告：{keyword}\n\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n> 系统版本：Coupang Product Selection System v1.0",
            "en_US": f"# Coupang Product Selection Report: {keyword}\n\n> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n> System: Coupang Product Selection System v1.0",
            "ko_KR": f"# 쿠팡 상품 선정 분석 보고서: {keyword}\n\n> 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n> 시스템: Coupang Product Selection System v1.0",
        }
        return titles.get(lang, titles["zh_CN"])

    def _section_market_overview(self, keyword: str, products: list, category: dict, lang: str) -> str:
        headers = {"zh_CN": "## 一、市场概况", "en_US": "## 1. Market Overview", "ko_KR": "## 1. 시장 개요"}
        lines = [headers.get(lang, headers["zh_CN"])]

        if category:
            # GMV
            gmv = category.get("gmv_estimate", {})
            if gmv:
                monthly_gmv = gmv.get("monthly_gmv_krw", 0)
                lines.append(f"\n**{'月度GMV预估' if lang=='zh_CN' else 'Monthly GMV Estimate' if lang=='en_US' else '월 GMV 추정'}**: {monthly_gmv:,.0f} KRW")

            # 垄断程度
            monopoly = category.get("monopoly_analysis", {})
            if monopoly.get("available"):
                lines.append(f"\n**{'垄断程度' if lang=='zh_CN' else 'Monopoly Level' if lang=='en_US' else '독점 수준'}**: {monopoly.get('description', '')}")
                lines.append(f"- Top1 占比: {monopoly.get('top1_ratio', 0)*100:.1f}%")
                lines.append(f"- Top3 占比: {monopoly.get('top3_ratio', 0)*100:.1f}%")
                lines.append(f"- Top10 占比: {monopoly.get('top10_ratio', 0)*100:.1f}%")

            # 新品占比
            new_prod = category.get("new_product_analysis", {})
            if new_prod:
                lines.append(f"\n**{'新品占比' if lang=='zh_CN' else 'New Product Ratio' if lang=='en_US' else '신제품 비율'}**:")
                lines.append(f"- 3个月内新品: {new_prod.get('new_3m_count', 0)} ({new_prod.get('new_3m_ratio', 0)*100:.1f}%)")
                lines.append(f"- 市场成熟度: {new_prod.get('market_maturity', 'unknown')}")

            # 价格分布
            price = category.get("price_distribution", {})
            if price.get("available"):
                lines.append(f"\n**{'价格分布' if lang=='zh_CN' else 'Price Distribution' if lang=='en_US' else '가격 분포'}**:")
                lines.append(f"\n| {'指标' if lang=='zh_CN' else 'Metric'} | {'值 (KRW)' if lang=='zh_CN' else 'Value (KRW)'} |")
                lines.append("|---|---|")
                lines.append(f"| {'最低价' if lang=='zh_CN' else 'Min'} | {price.get('min', 0):,.0f} |")
                lines.append(f"| {'最高价' if lang=='zh_CN' else 'Max'} | {price.get('max', 0):,.0f} |")
                lines.append(f"| {'均价' if lang=='zh_CN' else 'Average'} | {price.get('avg', 0):,.0f} |")
                lines.append(f"| {'中位数' if lang=='zh_CN' else 'Median'} | {price.get('median', 0):,.0f} |")

        return "\n".join(lines)

    def _section_competitor_analysis(self, products: list, reviews: dict, details: dict, lang: str) -> str:
        headers = {"zh_CN": "## 二、竞品分析", "en_US": "## 2. Competitor Analysis", "ko_KR": "## 2. 경쟁 분석"}
        lines = [headers.get(lang, headers["zh_CN"])]

        # 产品列表表格
        lines.append(f"\n### {'Top 产品列表' if lang=='zh_CN' else 'Top Products' if lang=='en_US' else '상위 제품 목록'}")
        lines.append(f"\n| # | {'产品名称' if lang=='zh_CN' else 'Product'} | {'价格' if lang=='zh_CN' else 'Price'} | {'评分' if lang=='zh_CN' else 'Rating'} | {'评论数' if lang=='zh_CN' else 'Reviews'} | {'配送' if lang=='zh_CN' else 'Delivery'} |")
        lines.append("|---|---|---|---|---|---|")

        for i, p in enumerate(products[:20]):
            title = p.get("title", "")[:30]
            price = f"{p.get('price', 0):,.0f}" if p.get("price") else "N/A"
            rating = p.get("rating", "N/A")
            review_count = p.get("review_count", 0)
            delivery = p.get("delivery_type", "unknown")
            lines.append(f"| {i+1} | {title} | {price} | {rating} | {review_count} | {delivery} |")

        # 评论分析摘要
        if reviews:
            lines.append(f"\n### {'评论分析摘要' if lang=='zh_CN' else 'Review Analysis Summary' if lang=='en_US' else '리뷰 분석 요약'}")
            for pid, analysis in list(reviews.items())[:5]:
                selling = analysis.get("selling_points", [])[:3]
                pain = analysis.get("pain_points", [])[:3]
                if selling:
                    sp_text = ", ".join([s.get("point", "") for s in selling])
                    lines.append(f"\n**{pid}** - {'卖点' if lang=='zh_CN' else 'Selling Points'}: {sp_text}")
                if pain:
                    pp_text = ", ".join([p.get("point", "") for p in pain])
                    lines.append(f"**{pid}** - {'痛点' if lang=='zh_CN' else 'Pain Points'}: {pp_text}")

        return "\n".join(lines)

    def _section_profit_analysis(self, profit_results: list, lang: str) -> str:
        headers = {"zh_CN": "## 三、利润分析", "en_US": "## 3. Profit Analysis", "ko_KR": "## 3. 수익 분석"}
        lines = [headers.get(lang, headers["zh_CN"])]

        if not profit_results:
            lines.append(f"\n{'暂无利润数据' if lang=='zh_CN' else 'No profit data available'}")
            return "\n".join(lines)

        lines.append(f"\n| {'货源' if lang=='zh_CN' else 'Source'} | {'采购价(RMB)' if lang=='zh_CN' else 'Cost(RMB)'} | {'售价(KRW)' if lang=='zh_CN' else 'Price(KRW)'} | {'利润(KRW)' if lang=='zh_CN' else 'Profit(KRW)'} | {'利润率' if lang=='zh_CN' else 'Margin'} | ROI |")
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

        return "\n".join(lines)

    def _section_opportunities_risks(self, category: dict, lang: str) -> str:
        headers = {"zh_CN": "## 四、机会与风险", "en_US": "## 4. Opportunities & Risks", "ko_KR": "## 4. 기회와 위험"}
        lines = [headers.get(lang, headers["zh_CN"])]

        ai_assess = category.get("ai_assessment", {}) if category else {}

        if ai_assess:
            # 机会
            opps = ai_assess.get("opportunities", [])
            if opps:
                lines.append(f"\n### {'市场机会' if lang=='zh_CN' else 'Opportunities' if lang=='en_US' else '시장 기회'}")
                for i, opp in enumerate(opps):
                    lines.append(f"{i+1}. {opp}")

            # 风险
            risks = ai_assess.get("risks", [])
            if risks:
                lines.append(f"\n### {'风险提示' if lang=='zh_CN' else 'Risks' if lang=='en_US' else '위험 요소'}")
                for i, risk in enumerate(risks):
                    lines.append(f"{i+1}. {risk}")

            # 进入策略
            strategy = ai_assess.get("entry_strategy", "")
            if strategy:
                lines.append(f"\n### {'建议进入策略' if lang=='zh_CN' else 'Entry Strategy' if lang=='en_US' else '진입 전략'}")
                lines.append(strategy)

        return "\n".join(lines)

    def _section_ai_recommendation(self, keyword: str, category: dict, profit: list, lang: str) -> str:
        headers = {"zh_CN": "## 五、AI 综合建议", "en_US": "## 5. AI Recommendation", "ko_KR": "## 5. AI 종합 권고"}
        lines = [headers.get(lang, headers["zh_CN"])]

        output_lang = {"zh_CN": "Chinese", "en_US": "English", "ko_KR": "Korean"}.get(lang, "Chinese")

        prompt = f"""Based on the following Coupang market analysis for keyword "{keyword}", provide a final recommendation.

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
            lines.append(f"\n{'AI建议生成失败' if lang=='zh_CN' else 'AI recommendation generation failed'}")

        return "\n".join(lines)

    def _section_appendix(self, products: list, lang: str) -> str:
        headers = {"zh_CN": "## 附录", "en_US": "## Appendix", "ko_KR": "## 부록"}
        lines = [headers.get(lang, headers["zh_CN"])]
        lines.append(f"\n{'分析产品总数' if lang=='zh_CN' else 'Total Products Analyzed'}: {len(products)}")
        lines.append(f"{'报告生成时间' if lang=='zh_CN' else 'Report Generated'}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"\n---\n*{'本报告由 Coupang 选品系统自动生成' if lang=='zh_CN' else 'This report was auto-generated by Coupang Product Selection System'}*")
        return "\n".join(lines)
