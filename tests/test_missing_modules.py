"""
缺失模块补全测试

测试 4 个新创建的模块：
  1. analysis.ai_analyzer.AIAnalyzer
  2. analysis.review_analyzer (ReviewAnalyzer, ReviewBatchAnalyzer, ReviewStatistics)
  3. analysis.risk_scoring (RiskScoring, FiveDimensionRadar)
  4. analysis.profit_analysis.amazon_fba_calculator (AmazonFBAProfitCalculator)
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ================================================================
# Test 1: AIAnalyzer
# ================================================================
class TestAIAnalyzer:
    """测试统一 AI 分析器"""

    def test_import(self):
        from analysis.ai_analyzer import AIAnalyzer
        assert AIAnalyzer is not None

    def test_init_without_client(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        assert analyzer.ai_client is None
        assert analyzer.detail_analyzer is not None
        assert analyzer.review_analyzer is not None
        assert analyzer.risk_analyzer is not None
        assert analyzer.summarizer is not None

    def test_init_with_client(self):
        from analysis.ai_analyzer import AIAnalyzer
        mock_client = MagicMock()
        analyzer = AIAnalyzer(ai_client=mock_client, ai_model="gpt-4.1-mini")
        assert analyzer.ai_client == mock_client
        assert analyzer.ai_model == "gpt-4.1-mini"

    def test_full_analysis_basic(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        product = {"asin": "B001TEST", "title": "Test Product", "price": 29.99}
        result = analyzer.full_analysis(product)
        assert "asin" in result
        assert "title" in result
        assert "analysis_timestamp" in result
        assert "detail_analysis" in result
        assert "review_analysis" in result
        assert "risk_analysis" in result
        assert "final_report" in result
        assert "analysis_duration_seconds" in result

    def test_full_analysis_with_reviews(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        product = {"asin": "B001TEST", "title": "Test Product"}
        reviews = [
            {"rating": 5, "content": "Great product!", "review_date": "2025-01-01"},
            {"rating": 3, "content": "Average quality", "review_date": "2025-01-15"},
        ]
        result = analyzer.full_analysis(product, reviews=reviews)
        assert result["review_analysis"]["total_reviews"] == 2

    def test_analyze_detail(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        product = {"asin": "B001TEST", "title": "Test Product", "price": 19.99}
        result = analyzer.analyze_detail(product)
        assert isinstance(result, dict)

    def test_analyze_reviews(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        reviews = [
            {"rating": 5, "content": "Excellent!", "review_date": "2025-01-01"},
            {"rating": 4, "content": "Good value", "review_date": "2025-02-01"},
        ]
        result = analyzer.analyze_reviews(reviews, "Test Product")
        assert "total_reviews" in result
        assert result["total_reviews"] == 2

    def test_analyze_risks(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        product = {"asin": "B001TEST", "title": "Generic Wireless Earbuds", "brand": "Generic"}
        result = analyzer.analyze_risks(product)
        assert "risk_score" in result
        assert "risk_level" in result

    def test_generate_summary(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        data = {
            "asin": "B001TEST",
            "title": "Test Product",
            "price": 29.99,
            "brand": "TestBrand",
            "profit": {"profit": {"profit_margin": "35%"}},
            "category_analysis": {"competition": {"competition_level": "中等竞争"}},
        }
        result = analyzer.generate_summary(data)
        assert "product_score" in result
        assert "decision" in result

    def test_batch_analyze(self):
        from analysis.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        products = [
            {"asin": "B001", "title": "Product 1", "price": 19.99},
            {"asin": "B002", "title": "Product 2", "price": 29.99},
        ]
        results = analyzer.batch_analyze(products)
        assert len(results) == 2


# ================================================================
# Test 2: ReviewAnalyzer (top-level), ReviewBatchAnalyzer, ReviewStatistics
# ================================================================
class TestReviewAnalyzerTopLevel:
    """测试顶层评论分析器"""

    def test_import_review_analyzer(self):
        from analysis.review_analyzer import ReviewAnalyzer
        assert ReviewAnalyzer is not None

    def test_import_batch_analyzer(self):
        from analysis.review_analyzer import ReviewBatchAnalyzer
        assert ReviewBatchAnalyzer is not None

    def test_import_statistics(self):
        from analysis.review_analyzer import ReviewStatistics
        assert ReviewStatistics is not None

    def test_review_analyzer_is_same_class(self):
        """确认顶层 ReviewAnalyzer 和 ai_analysis 中的是同一个类"""
        from analysis.review_analyzer import ReviewAnalyzer as RA1
        from analysis.ai_analysis.review_analyzer import ReviewAnalyzer as RA2
        assert RA1 is RA2


class TestReviewStatistics:
    """测试评论统计工具"""

    def setup_method(self):
        self.reviews = [
            {"rating": 5, "content": "Amazing product very good quality", "review_date": "2025-01-01"},
            {"rating": 5, "content": "Love it great value", "review_date": "2025-01-05"},
            {"rating": 4, "content": "Good but could be better packaging", "review_date": "2025-01-10"},
            {"rating": 3, "content": "Average quality nothing special", "review_date": "2025-02-01"},
            {"rating": 2, "content": "Poor quality broke after a week", "review_date": "2025-02-15"},
            {"rating": 1, "content": "Terrible waste of money", "review_date": "2025-03-01"},
        ]

    def test_rating_distribution(self):
        from analysis.review_analyzer import ReviewStatistics
        stats = ReviewStatistics.rating_distribution(self.reviews)
        assert stats["total"] == 6
        assert stats["distribution"][5]["count"] == 2
        assert stats["distribution"][1]["count"] == 1
        assert 0 < stats["average_rating"] < 5
        assert "positive_ratio" in stats
        assert "negative_ratio" in stats

    def test_rating_distribution_empty(self):
        from analysis.review_analyzer import ReviewStatistics
        stats = ReviewStatistics.rating_distribution([])
        assert stats["total"] == 0
        assert stats["average_rating"] == 0

    def test_review_trend_monthly(self):
        from analysis.review_analyzer import ReviewStatistics
        trend = ReviewStatistics.review_trend(self.reviews, granularity="month")
        assert "2025-01" in trend
        assert trend["2025-01"]["count"] == 3

    def test_review_trend_weekly(self):
        from analysis.review_analyzer import ReviewStatistics
        trend = ReviewStatistics.review_trend(self.reviews, granularity="week")
        assert len(trend) > 0

    def test_detect_suspicious_reviews(self):
        from analysis.review_analyzer import ReviewStatistics
        # 添加一些可疑评论
        suspicious_reviews = self.reviews + [
            {"rating": 5, "content": "Good", "review_date": "2025-04-01"},
            {"rating": 5, "content": "Nice", "review_date": "2025-04-01"},
            {"rating": 5, "content": "OK", "review_date": "2025-04-01"},
        ]
        result = ReviewStatistics.detect_suspicious_reviews(suspicious_reviews)
        assert "total_reviews" in result
        assert "suspicious_count" in result
        assert "suspicious_ratio" in result
        assert "risk_level" in result

    def test_keyword_frequency(self):
        from analysis.review_analyzer import ReviewStatistics
        keywords = ReviewStatistics.keyword_frequency(self.reviews, top_n=10)
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "keyword" in keywords[0]
        assert "count" in keywords[0]

    def test_keyword_frequency_empty(self):
        from analysis.review_analyzer import ReviewStatistics
        keywords = ReviewStatistics.keyword_frequency([], top_n=10)
        assert keywords == []


class TestReviewBatchAnalyzer:
    """测试批量评论分析器"""

    def test_init(self):
        from analysis.review_analyzer import ReviewBatchAnalyzer
        analyzer = ReviewBatchAnalyzer()
        assert analyzer.analyzer is not None
        assert analyzer.stats is not None

    def test_batch_analyze(self):
        from analysis.review_analyzer import ReviewBatchAnalyzer
        analyzer = ReviewBatchAnalyzer()
        products_reviews = {
            "B001": [
                {"rating": 5, "content": "Great!", "review_date": "2025-01-01"},
                {"rating": 4, "content": "Good value", "review_date": "2025-01-15"},
            ],
            "B002": [
                {"rating": 3, "content": "Average", "review_date": "2025-02-01"},
            ],
        }
        results = analyzer.batch_analyze(products_reviews)
        assert "B001" in results
        assert "B002" in results

    def test_compare_reviews(self):
        from analysis.review_analyzer import ReviewBatchAnalyzer
        analyzer = ReviewBatchAnalyzer()
        products_reviews = {
            "B001": [
                {"rating": 5, "content": "Great!", "review_date": "2025-01-01"},
                {"rating": 5, "content": "Excellent!", "review_date": "2025-01-15"},
            ],
            "B002": [
                {"rating": 3, "content": "Average", "review_date": "2025-02-01"},
            ],
        }
        comparison = analyzer.compare_reviews(products_reviews)
        assert comparison["best_rated"] == "B001"
        assert comparison["most_reviewed"] == "B001"
        assert "products" in comparison


# ================================================================
# Test 3: RiskScoring, FiveDimensionRadar
# ================================================================
class TestFiveDimensionRadar:
    """测试五维风险雷达图"""

    def test_init_default(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar()
        assert radar.competition == 0
        assert radar.demand == 0
        assert radar.profit == 0
        assert radar.ip_risk == 0
        assert radar.seasonality == 0

    def test_init_with_values(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=50, demand=30, profit=40, ip_risk=20, seasonality=10)
        assert radar.competition == 50
        assert radar.demand == 30
        assert radar.profit == 40
        assert radar.ip_risk == 20
        assert radar.seasonality == 10

    def test_clamping(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=150, demand=-10)
        assert radar.competition == 100
        assert radar.demand == 0

    def test_overall_score(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=50, demand=30, profit=40, ip_risk=20, seasonality=10)
        score = radar.overall_score
        assert 0 <= score <= 100
        # 加权: 50*0.25 + 30*0.20 + 40*0.25 + 20*0.20 + 10*0.10 = 12.5+6+10+4+1 = 33.5
        assert score == 33.5

    def test_risk_level_low(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=10, demand=10, profit=10, ip_risk=10, seasonality=10)
        assert radar.risk_level == "极低"

    def test_risk_level_high(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=80, demand=70, profit=60, ip_risk=50, seasonality=40)
        assert radar.risk_level in ("高", "极高")

    def test_to_dict(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=50, demand=30, profit=40, ip_risk=20, seasonality=10)
        d = radar.to_dict()
        assert "dimensions" in d
        assert "labels" in d
        assert "values" in d
        assert "overall_score" in d
        assert "risk_level" in d
        assert len(d["labels"]) == 5
        assert len(d["values"]) == 5

    def test_to_chart_data(self):
        from analysis.risk_scoring import FiveDimensionRadar
        radar = FiveDimensionRadar(competition=50, demand=30, profit=40, ip_risk=20, seasonality=10)
        chart = radar.to_chart_data()
        assert chart["type"] == "radar"
        assert "data" in chart
        assert "options" in chart
        assert len(chart["data"]["datasets"]) == 1
        assert len(chart["data"]["datasets"][0]["data"]) == 5


class TestRiskScoring:
    """测试风险评分引擎"""

    def test_init(self):
        from analysis.risk_scoring import RiskScoring
        scorer = RiskScoring()
        assert scorer.risk_analyzer is not None

    def test_calculate_radar_basic(self):
        from analysis.risk_scoring import RiskScoring
        scorer = RiskScoring()
        product = {
            "asin": "B001TEST",
            "title": "Generic Wireless Earbuds",
            "brand": "Generic",
            "price": 29.99,
        }
        radar = scorer.calculate_radar(product)
        assert 0 <= radar.competition <= 100
        assert 0 <= radar.demand <= 100
        assert 0 <= radar.profit <= 100
        assert 0 <= radar.ip_risk <= 100
        assert 0 <= radar.seasonality <= 100

    def test_calculate_radar_high_ip_risk(self):
        from analysis.risk_scoring import RiskScoring
        scorer = RiskScoring()
        product = {
            "asin": "B001TEST",
            "title": "Disney Princess Toy",
            "brand": "Disney",
        }
        radar = scorer.calculate_radar(product)
        assert radar.ip_risk >= 40  # Disney 应触发高 IP 风险

    def test_full_risk_report(self):
        from analysis.risk_scoring import RiskScoring
        scorer = RiskScoring()
        product = {
            "asin": "B001TEST",
            "title": "Test Product",
            "brand": "TestBrand",
            "price": 25.00,
        }
        report = scorer.full_risk_report(product)
        assert "radar" in report
        assert "chart_data" in report
        assert "detailed_analysis" in report
        assert "recommendations" in report
        assert "generated_at" in report

    def test_recommendations_generated(self):
        from analysis.risk_scoring import RiskScoring
        scorer = RiskScoring()
        product = {
            "asin": "B001TEST",
            "title": "Test Product",
            "brand": "",
        }
        report = scorer.full_risk_report(product)
        assert len(report["recommendations"]) > 0
        rec = report["recommendations"][0]
        assert "dimension" in rec
        assert "suggestion" in rec
        assert "actions" in rec

    def test_batch_score(self):
        from analysis.risk_scoring import RiskScoring
        scorer = RiskScoring()
        products = [
            {"asin": "B001", "title": "Product 1", "brand": "Brand1"},
            {"asin": "B002", "title": "Disney Toy", "brand": "Disney"},
        ]
        results = scorer.batch_score(products)
        assert len(results) == 2
        # 应按风险从低到高排序
        assert results[0].get("overall_risk", 100) <= results[1].get("overall_risk", 100)


# ================================================================
# Test 4: AmazonFBAProfitCalculator (alias)
# ================================================================
class TestAmazonFBACalculatorAlias:
    """测试 Amazon FBA 利润计算器别名导入"""

    def test_import_from_alias(self):
        from analysis.profit_analysis.amazon_fba_calculator import AmazonFBAProfitCalculator
        assert AmazonFBAProfitCalculator is not None

    def test_import_from_original(self):
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator
        assert AmazonFBAProfitCalculator is not None

    def test_same_class(self):
        """确认别名和原始导入是同一个类"""
        from analysis.profit_analysis.amazon_fba_calculator import AmazonFBAProfitCalculator as C1
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator as C2
        assert C1 is C2

    def test_instantiation(self):
        from analysis.profit_analysis.amazon_fba_calculator import AmazonFBAProfitCalculator
        calc = AmazonFBAProfitCalculator()
        assert calc is not None

    def test_has_calculate_method(self):
        from analysis.profit_analysis.amazon_fba_calculator import AmazonFBAProfitCalculator
        calc = AmazonFBAProfitCalculator()
        assert hasattr(calc, "calculate_profit")


# ================================================================
# Test 5: 全模块导入完整性验证
# ================================================================
class TestAllModulesImport:
    """验证所有分析模块都可以正确导入"""

    def test_all_analysis_modules(self):
        """测试所有 analysis 子模块的导入"""
        modules = [
            ("analysis.ai_analyzer", "AIAnalyzer"),
            ("analysis.review_analyzer", "ReviewAnalyzer"),
            ("analysis.risk_scoring", "RiskScoring"),
            ("analysis.risk_scoring", "FiveDimensionRadar"),
            ("analysis.data_filter", "DataFilter"),
            ("analysis.amazon_data_filter", "AmazonDataFilter"),
            ("analysis.keyword_researcher", "KeywordResearcher"),
            ("analysis.bsr_tracker", "BSRTracker"),
            ("analysis.competitor_finder", "CompetitorFinder"),
            ("analysis.competitor_tracker", "CompetitorTracker"),
            ("analysis.sentiment_visualizer", "SentimentVisualizer"),
            ("analysis.supplier_scorer", "SupplierScorer"),
            ("analysis.pricing_optimizer", "PricingOptimizer"),
            ("analysis.dashboard_analytics", "DashboardAnalytics"),
            ("analysis.ai_analysis.product_decision_engine", "ProductDecisionEngine"),
            ("analysis.ai_analysis.detail_analyzer", "DetailPageAnalyzer"),
            ("analysis.ai_analysis.review_analyzer", "ReviewAnalyzer"),
            ("analysis.ai_analysis.risk_analyzer", "RiskAnalyzer"),
            ("analysis.market_analysis.category_analyzer", "CategoryAnalyzer"),
            ("analysis.market_analysis.report_generator", "ReportGenerator"),
            ("analysis.profit_analysis.profit_calculator", "ProfitCalculator"),
            ("analysis.profit_analysis.amazon_profit_calculator", "AmazonFBAProfitCalculator"),
            ("analysis.profit_analysis.amazon_fba_calculator", "AmazonFBAProfitCalculator"),
        ]

        import importlib
        failed = []
        for mod_name, class_name in modules:
            try:
                mod = importlib.import_module(mod_name)
                cls = getattr(mod, class_name)
                assert cls is not None
            except Exception as e:
                failed.append(f"{mod_name}.{class_name}: {e}")

        if failed:
            pytest.fail(f"Failed to import {len(failed)} modules:\n" + "\n".join(failed))
