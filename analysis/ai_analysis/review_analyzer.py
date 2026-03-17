"""
Coupang 选品系统 - AI 评论分析模块
功能:
  1. 评论痛点与卖点提取
  2. 人群画像分析
  3. SKU属性销量分布
  4. 评分分布统计
  5. 刷单检测辅助
"""

import json
import os
from typing import Optional
from collections import Counter, defaultdict

from utils.logger import get_logger
from i18n import t, get_language

logger = get_logger()


class ReviewAnalyzer:
    """
    AI 评论分析器
    使用 OpenAI GPT 对评论进行多维度深度分析
    """

    def __init__(self, ai_client=None):
        """
        :param ai_client: OpenAI 客户端实例
        """
        self.ai_client = ai_client

    def analyze(self, reviews: list[dict], product_title: str = "") -> dict:
        """
        对产品评论进行全面分析

        :param reviews: 评论列表
        :param product_title: 产品标题（提供上下文）
        :return: 分析结果字典
        """
        logger.info(t("analysis.review_analysis_start"))

        # 1. 基础统计
        basic_stats = self._basic_statistics(reviews)

        # 2. SKU属性分布
        sku_distribution = self._sku_distribution(reviews)

        # 3. AI深度分析（卖点、痛点、人群画像）
        ai_insights = {}
        if self.ai_client:
            ai_insights = self._ai_deep_analysis(reviews, product_title)

        # 4. 推算上架时间
        earliest_date = self._find_earliest_review_date(reviews)

        result = {
            **basic_stats,
            "sku_sales_distribution": sku_distribution,
            "selling_points": ai_insights.get("selling_points", []),
            "pain_points": ai_insights.get("pain_points", []),
            "audience_profile": ai_insights.get("audience_profile", {}),
            "improvement_suggestions": ai_insights.get("improvement_suggestions", []),
            "earliest_review_date": earliest_date,
        }

        logger.info(t("analysis.analysis_complete"))
        return result

    def _basic_statistics(self, reviews: list[dict]) -> dict:
        """基础统计: 评分分布、平均评分等"""
        # 过滤掉疑似刷单的评论
        valid_reviews = [r for r in reviews if not r.get("is_suspicious", False)]

        total = len(valid_reviews)
        if total == 0:
            return {
                "total_reviews": 0,
                "avg_rating": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }

        # 评分分布
        rating_counts = Counter()
        for r in valid_reviews:
            rating = r.get("rating", 0)
            if 1 <= rating <= 5:
                rating_counts[rating] += 1

        avg_rating = sum(r.get("rating", 0) for r in valid_reviews if r.get("rating")) / max(
            sum(1 for r in valid_reviews if r.get("rating")), 1
        )

        return {
            "total_reviews": total,
            "avg_rating": round(avg_rating, 2),
            "rating_distribution": {
                1: rating_counts.get(1, 0),
                2: rating_counts.get(2, 0),
                3: rating_counts.get(3, 0),
                4: rating_counts.get(4, 0),
                5: rating_counts.get(5, 0),
            },
            "suspicious_count": sum(1 for r in reviews if r.get("is_suspicious", False)),
        }

    def _sku_distribution(self, reviews: list[dict]) -> dict:
        """统计各SKU属性的销量分布"""
        sku_counts = Counter()
        for r in reviews:
            sku = r.get("sku_attribute", "").strip()
            if sku:
                sku_counts[sku] += 1

        total = sum(sku_counts.values())
        if total == 0:
            return {}

        distribution = {}
        for sku, count in sku_counts.most_common():
            distribution[sku] = {
                "count": count,
                "ratio": round(count / total, 4),
                "percentage": f"{count / total * 100:.1f}%",
            }

        return distribution

    def _ai_deep_analysis(self, reviews: list[dict], product_title: str) -> dict:
        """
        使用AI进行深度分析

        分析维度:
        - 卖点提取（用户好评的核心原因）
        - 痛点提取（用户差评的核心原因）
        - 人群画像（购买者特征推断）
        - 改进建议
        """
        logger.info(t("analysis.ai_analyzing"))

        # 准备评论文本（取最多200条有内容的评论）
        review_texts = []
        for r in reviews:
            content = r.get("content", "").strip()
            if content and len(content) > 3:
                rating = r.get("rating", "?")
                sku = r.get("sku_attribute", "")
                text = f"[{rating}★] {content}"
                if sku:
                    text += f" (SKU: {sku})"
                review_texts.append(text)

        if not review_texts:
            return {}

        # 限制输入长度
        sample = review_texts[:200]
        reviews_block = "\n".join(sample)

        # 根据当前语言选择输出语言
        lang = get_language()
        output_lang = {
            "zh_CN": "Chinese (Simplified)",
            "en_US": "English",
            "ko_KR": "Korean",
        }.get(lang, "Chinese (Simplified)")

        prompt = f"""You are an expert e-commerce product analyst for Coupang (Korean marketplace).

Product: {product_title}
Total reviews analyzed: {len(reviews)}
Sample reviews ({len(sample)} shown):

{reviews_block}

Please analyze these reviews and provide a structured JSON response with the following:

1. "selling_points": Top 5-8 selling points (what customers love), each with:
   - "point": description
   - "frequency": how often mentioned (high/medium/low)
   - "example_quote": a representative review quote

2. "pain_points": Top 5-8 pain points (what customers complain about), each with:
   - "point": description
   - "severity": impact level (high/medium/low)
   - "example_quote": a representative review quote

3. "audience_profile": Customer profile analysis:
   - "primary_use_cases": main usage scenarios
   - "buyer_demographics": inferred buyer characteristics
   - "purchase_motivations": why they buy
   - "price_sensitivity": price sensitivity level

4. "improvement_suggestions": Top 3-5 actionable improvement suggestions for a new seller entering this market

Respond in {output_lang}. Return ONLY valid JSON, no other text."""

        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3000,
            )
            result_text = response.choices[0].message.content.strip()

            # 清理JSON
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            return json.loads(result_text)

        except json.JSONDecodeError as e:
            logger.error(f"AI response JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {}

    def _find_earliest_review_date(self, reviews: list[dict]) -> Optional[str]:
        """找到最早的评论日期（用于推算上架时间）"""
        dates = []
        for r in reviews:
            date_str = r.get("review_date", "")
            if date_str:
                # 只取日期部分
                date_part = str(date_str)[:10]
                if len(date_part) == 10:
                    dates.append(date_part)

        return min(dates) if dates else None
