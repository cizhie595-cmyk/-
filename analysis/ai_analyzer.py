"""
顶层 AI 分析器 - 统一入口模块

整合所有 AI 分析子模块，提供统一的分析接口：
  - 详情页分析（DetailPageAnalyzer）
  - 评论分析（ReviewAnalyzer）
  - 风险分析（RiskAnalyzer）
  - 综合评分与决策（AIProductSummarizer）

使用方式:
    from analysis.ai_analyzer import AIAnalyzer
    analyzer = AIAnalyzer(ai_client=openai_client)
    result = analyzer.full_analysis(product_data, reviews, detail_images)
"""

import json
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()

# 导入子模块
from analysis.ai_analysis.detail_analyzer import DetailPageAnalyzer
from analysis.ai_analysis.review_analyzer import ReviewAnalyzer
from analysis.ai_analysis.risk_analyzer import RiskAnalyzer, AIProductSummarizer


class AIAnalyzer:
    """
    统一 AI 分析器

    整合详情页分析、评论分析、风险分析和综合决策，
    提供一站式产品分析能力。

    Attributes:
        detail_analyzer: 详情页分析器实例
        review_analyzer: 评论分析器实例
        risk_analyzer: 风险分析器实例
        summarizer: 综合总结器实例
    """

    def __init__(self, ai_client=None, ai_model: str = "gpt-4.1-mini"):
        """
        初始化 AI 分析器

        :param ai_client: OpenAI 客户端实例（可选，无则跳过 AI 分析）
        :param ai_model: 使用的 AI 模型名称
        """
        self.ai_client = ai_client
        self.ai_model = ai_model

        self.detail_analyzer = DetailPageAnalyzer(ai_client=ai_client)
        self.review_analyzer = ReviewAnalyzer(ai_client=ai_client)
        self.risk_analyzer = RiskAnalyzer(ai_client=ai_client, ai_model=ai_model)
        self.summarizer = AIProductSummarizer(ai_client=ai_client, ai_model=ai_model)

    def full_analysis(
        self,
        product_data: dict,
        reviews: list[dict] = None,
        detail_images: list[str] = None,
        category_analysis: dict = None,
        profit_data: dict = None,
    ) -> dict:
        """
        对产品进行全面 AI 分析

        :param product_data: 产品基础数据（title, asin, price, brand, category 等）
        :param reviews: 评论列表
        :param detail_images: 详情页图片路径列表
        :param category_analysis: 类目分析数据（可选）
        :param profit_data: 利润分析数据（可选）
        :return: 完整分析结果
        """
        logger.info(f"[AIAnalyzer] 开始全面分析: {product_data.get('asin', 'N/A')}")
        start_time = datetime.now()

        result = {
            "asin": product_data.get("asin", ""),
            "title": product_data.get("title", ""),
            "analysis_timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 1. 详情页分析
        try:
            result["detail_analysis"] = self.detail_analyzer.analyze(
                product_data, detail_images or []
            )
            logger.info("[AIAnalyzer] 详情页分析完成")
        except Exception as e:
            logger.error(f"[AIAnalyzer] 详情页分析失败: {e}")
            result["detail_analysis"] = {"error": str(e)}

        # 2. 评论分析
        try:
            if reviews:
                result["review_analysis"] = self.review_analyzer.analyze(
                    reviews, product_data.get("title", "")
                )
            else:
                result["review_analysis"] = {
                    "total_reviews": 0,
                    "avg_rating": 0,
                    "note": "无评论数据",
                }
            logger.info("[AIAnalyzer] 评论分析完成")
        except Exception as e:
            logger.error(f"[AIAnalyzer] 评论分析失败: {e}")
            result["review_analysis"] = {"error": str(e)}

        # 3. 风险分析
        try:
            # 组装风险分析所需的完整数据
            risk_input = {
                **product_data,
                "category_analysis": category_analysis or {},
                "profit": profit_data or {},
                "detail": product_data.get("detail", {}),
                "deep_analysis": result.get("detail_analysis", {}),
            }
            result["risk_analysis"] = self.risk_analyzer.analyze_risks(risk_input)
            logger.info("[AIAnalyzer] 风险分析完成")
        except Exception as e:
            logger.error(f"[AIAnalyzer] 风险分析失败: {e}")
            result["risk_analysis"] = {"error": str(e), "risk_score": 50}

        # 4. 综合评分与决策
        try:
            summary_input = {
                **product_data,
                "category_analysis": category_analysis or {},
                "profit": profit_data or {},
                "risk_analysis": result.get("risk_analysis", {}),
                "deep_analysis": result.get("detail_analysis", {}),
            }
            result["final_report"] = self.summarizer.generate_final_report(summary_input)
            logger.info("[AIAnalyzer] 综合评分完成")
        except Exception as e:
            logger.error(f"[AIAnalyzer] 综合评分失败: {e}")
            result["final_report"] = {"error": str(e), "product_score": 0}

        # 5. 计算分析耗时
        elapsed = (datetime.now() - start_time).total_seconds()
        result["analysis_duration_seconds"] = round(elapsed, 2)

        logger.info(
            f"[AIAnalyzer] 全面分析完成: {product_data.get('asin', 'N/A')} "
            f"(耗时 {elapsed:.1f}s, 评分 {result.get('final_report', {}).get('product_score', 'N/A')})"
        )

        return result

    def analyze_detail(self, product_data: dict, detail_images: list[str] = None) -> dict:
        """
        仅执行详情页分析

        :param product_data: 产品基础数据
        :param detail_images: 详情页图片路径列表
        :return: 详情页分析结果
        """
        return self.detail_analyzer.analyze(product_data, detail_images or [])

    def analyze_reviews(self, reviews: list[dict], product_title: str = "") -> dict:
        """
        仅执行评论分析

        :param reviews: 评论列表
        :param product_title: 产品标题
        :return: 评论分析结果
        """
        return self.review_analyzer.analyze(reviews, product_title)

    def analyze_risks(self, product_data: dict) -> dict:
        """
        仅执行风险分析

        :param product_data: 产品完整数据
        :return: 风险分析报告
        """
        return self.risk_analyzer.analyze_risks(product_data)

    def generate_summary(self, all_data: dict) -> dict:
        """
        仅生成综合总结报告

        :param all_data: 所有分析数据汇总
        :return: 综合报告
        """
        return self.summarizer.generate_final_report(all_data)

    def batch_analyze(
        self,
        products: list[dict],
        reviews_map: dict = None,
        category_analysis: dict = None,
    ) -> list[dict]:
        """
        批量分析多个产品

        :param products: 产品列表
        :param reviews_map: {asin: [reviews]} 评论映射
        :param category_analysis: 共享的类目分析数据
        :return: 分析结果列表
        """
        reviews_map = reviews_map or {}
        results = []

        for i, product in enumerate(products):
            asin = product.get("asin", f"product_{i}")
            logger.info(f"[AIAnalyzer] 批量分析 [{i+1}/{len(products)}]: {asin}")

            try:
                result = self.full_analysis(
                    product_data=product,
                    reviews=reviews_map.get(asin, []),
                    category_analysis=category_analysis,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"[AIAnalyzer] 批量分析失败 {asin}: {e}")
                results.append({
                    "asin": asin,
                    "error": str(e),
                    "product_score": 0,
                })

        # 按评分排序
        results.sort(
            key=lambda x: x.get("final_report", {}).get("product_score", 0),
            reverse=True,
        )

        return results
