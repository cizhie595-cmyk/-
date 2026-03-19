"""
测试新增的产品洞察模块:
- BSR 历史追踪器 (bsr_tracker.py)
- 竞品发现引擎 (competitor_finder.py)
- 评论情感可视化 (sentiment_visualizer.py)
- AI 选品决策引擎 (product_decision_engine.py)
- 数据看板分析引擎 (dashboard_analytics.py)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# BSR Tracker Tests
# ============================================================
class TestBSRTracker:
    """BSR 历史追踪器测试"""

    def test_record_snapshot(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker(marketplace="US")
        snapshot = tracker.record_snapshot(
            asin="B0TEST001",
            snapshot_data={"bsr_rank": 1500, "price": 29.99, "rating": 4.5, "review_count": 120},
        )
        assert snapshot is not None
        assert snapshot["asin"] == "B0TEST001"
        assert snapshot["bsr_rank"] == 1500

    def test_record_snapshot_minimal(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        snapshot = tracker.record_snapshot(
            asin="B0TEST002",
            snapshot_data={},
        )
        assert snapshot is not None
        assert snapshot["asin"] == "B0TEST002"

    def test_batch_record(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        products = [
            {"asin": "B0BAT01", "bsr_rank": 100, "price": 19.99},
            {"asin": "B0BAT02", "bsr_rank": 200, "price": 29.99},
        ]
        results = tracker.batch_record(products)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_get_bsr_history(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        # 先记录多个快照
        for i in range(5):
            tracker.record_snapshot(asin="B0HIST01", snapshot_data={"bsr_rank": 1000 - i * 100, "price": 29.99})
        history = tracker.get_bsr_history(asin="B0HIST01", days=30)
        assert history is not None
        assert isinstance(history, dict)

    def test_get_price_history(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        tracker.record_snapshot(asin="B0PRICE1", snapshot_data={"price": 29.99})
        tracker.record_snapshot(asin="B0PRICE1", snapshot_data={"price": 24.99})
        history = tracker.get_price_history(asin="B0PRICE1", days=30)
        assert history is not None
        assert isinstance(history, dict)

    def test_get_full_trend_dashboard(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        tracker.record_snapshot(asin="B0DASH01", snapshot_data={"bsr_rank": 500, "price": 19.99, "review_count": 50})
        dashboard = tracker.get_full_trend_dashboard(asin="B0DASH01", days=30)
        assert dashboard is not None
        assert isinstance(dashboard, dict)

    def test_detect_anomalies(self):
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        for i in range(5):
            tracker.record_snapshot(asin="B0ANOM01", snapshot_data={"bsr_rank": 1000})
        tracker.record_snapshot(asin="B0ANOM01", snapshot_data={"bsr_rank": 50000})
        anomalies = tracker.detect_anomalies(asin="B0ANOM01", days=30)
        assert anomalies is not None


# ============================================================
# Competitor Finder Tests
# ============================================================
class TestCompetitorFinder:
    """竞品发现引擎测试"""

    SAMPLE_PRODUCTS = [
        {
            "asin": "B0COMP01", "title": "Wireless Bluetooth Earbuds",
            "price": 29.99, "rating": 4.3, "review_count": 500,
            "bsr_rank": 1200, "brand": "BrandA", "fulfillment_type": "FBA",
            "est_sales_30d": 800, "bsr_category": "Electronics",
        },
        {
            "asin": "B0COMP02", "title": "Wireless Earbuds Bluetooth 5.3",
            "price": 24.99, "rating": 4.1, "review_count": 300,
            "bsr_rank": 2500, "brand": "BrandB", "fulfillment_type": "FBA",
            "est_sales_30d": 500, "bsr_category": "Electronics",
        },
        {
            "asin": "B0COMP03", "title": "Premium Noise Cancelling Earbuds",
            "price": 59.99, "rating": 4.6, "review_count": 1200,
            "bsr_rank": 800, "brand": "BrandC", "fulfillment_type": "FBA",
            "est_sales_30d": 1500, "bsr_category": "Electronics",
        },
        {
            "asin": "B0COMP04", "title": "Budget Wireless Earphones",
            "price": 12.99, "rating": 3.8, "review_count": 150,
            "bsr_rank": 5000, "brand": "BrandD", "fulfillment_type": "FBM",
            "est_sales_30d": 200, "bsr_category": "Electronics",
        },
    ]

    def test_find_by_keyword(self):
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        result = finder.find_by_keyword(
            keyword="wireless earbuds",
            products=self.SAMPLE_PRODUCTS,
        )
        assert result is not None
        assert isinstance(result, (list, dict))

    def test_build_comparison_matrix(self):
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        matrix = finder.build_comparison_matrix(
            target=self.SAMPLE_PRODUCTS[0],
            competitors=self.SAMPLE_PRODUCTS[1:],
        )
        assert matrix is not None
        assert isinstance(matrix, dict)

    def test_analyze_competitive_landscape(self):
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        landscape = finder.analyze_competitive_landscape(products=self.SAMPLE_PRODUCTS)
        assert landscape is not None
        assert isinstance(landscape, dict)

    def test_analyze_landscape_empty(self):
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        landscape = finder.analyze_competitive_landscape(products=[])
        assert landscape is not None

    def test_find_by_category(self):
        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        result = finder.find_by_category(
            category="Electronics",
            products=self.SAMPLE_PRODUCTS,
        )
        assert result is not None
        assert isinstance(result, (list, dict))


# ============================================================
# Sentiment Visualizer Tests
# ============================================================
class TestSentimentVisualizer:
    """评论情感可视化测试"""

    SAMPLE_REVIEWS = [
        {"text": "Great product, love the sound quality!", "rating": 5, "title": "Amazing"},
        {"text": "Good value for money, decent quality", "rating": 4, "title": "Good"},
        {"text": "Average product, nothing special", "rating": 3, "title": "OK"},
        {"text": "Poor battery life, not worth the price", "rating": 2, "title": "Bad"},
        {"text": "Terrible quality, broke after one week", "rating": 1, "title": "Awful"},
        {"text": "Excellent noise cancellation, very comfortable", "rating": 5, "title": "Best"},
        {"text": "Sound is clear but bass could be better", "rating": 4, "title": "Nice"},
        {"text": "Comfortable fit, good for running", "rating": 4, "title": "Sports"},
    ]

    def test_generate_word_cloud_data(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        wordcloud = viz.generate_word_cloud_data(reviews=self.SAMPLE_REVIEWS)
        assert wordcloud is not None
        assert isinstance(wordcloud, (dict, list))

    def test_analyze_sentiment_trend(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        trend = viz.analyze_sentiment_trend(reviews=self.SAMPLE_REVIEWS)
        assert trend is not None
        assert isinstance(trend, dict)

    def test_extract_review_tags(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        tags = viz.extract_review_tags(reviews=self.SAMPLE_REVIEWS)
        assert tags is not None
        assert isinstance(tags, list)

    def test_analyze_rating_distribution(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        dist = viz.analyze_rating_distribution(reviews=self.SAMPLE_REVIEWS)
        assert dist is not None
        assert isinstance(dist, dict)

    def test_assess_review_quality(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        quality = viz.assess_review_quality(reviews=self.SAMPLE_REVIEWS)
        assert quality is not None
        assert isinstance(quality, dict)

    def test_generate_full_visualization(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        result = viz.generate_full_visualization(reviews=self.SAMPLE_REVIEWS)
        assert result is not None
        assert isinstance(result, dict)

    def test_empty_reviews(self):
        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        result = viz.generate_full_visualization(reviews=[])
        assert result is not None


# ============================================================
# Product Decision Engine Tests
# ============================================================
class TestProductDecisionEngine:
    """AI 选品决策引擎测试"""

    SAMPLE_PRODUCT = {
        "asin": "B0DEC001", "title": "Wireless Earbuds",
        "price": 29.99, "rating": 4.3, "review_count": 500,
        "bsr_rank": 1200, "est_sales_30d": 800, "brand": "TestBrand",
        "fulfillment_type": "FBA",
    }

    SAMPLE_MARKET = {
        "avg_price": 35.0, "avg_rating": 4.2,
        "total_products": 50, "fba_ratio": 0.7,
    }

    SAMPLE_PROFIT = {
        "selling_price_usd": 29.99, "profit_per_unit_usd": 8.50,
        "profit_margin_pct": 28.3, "roi_pct": 120.0,
    }

    def test_evaluate_product(self):
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine(ai_client=None)
        result = engine.evaluate_product(
            product_data=self.SAMPLE_PRODUCT,
            market_data=self.SAMPLE_MARKET,
            profit_data=self.SAMPLE_PROFIT,
        )
        assert result is not None
        assert isinstance(result, dict)
        # 应该有决策和评分
        assert "decision" in result or "overall_score" in result

    def test_evaluate_no_profit(self):
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine(ai_client=None)
        result = engine.evaluate_product(
            product_data=self.SAMPLE_PRODUCT,
            market_data=self.SAMPLE_MARKET,
        )
        assert result is not None

    def test_evaluate_empty_product(self):
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine(ai_client=None)
        result = engine.evaluate_product(product_data={}, market_data={})
        assert result is not None

    def test_batch_evaluate(self):
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine(ai_client=None)
        products = [self.SAMPLE_PRODUCT, {**self.SAMPLE_PRODUCT, "asin": "B0DEC002", "price": 19.99}]
        result = engine.batch_evaluate(
            products=products,
            market_data=self.SAMPLE_MARKET,
            profit_results=[self.SAMPLE_PROFIT, self.SAMPLE_PROFIT],
        )
        assert result is not None
        assert isinstance(result, dict)

    def test_decision_has_score(self):
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine(ai_client=None)
        result = engine.evaluate_product(
            product_data=self.SAMPLE_PRODUCT,
            market_data=self.SAMPLE_MARKET,
            profit_data=self.SAMPLE_PROFIT,
        )
        assert "overall_score" in result
        assert isinstance(result["overall_score"], (int, float))
        assert 0 <= result["overall_score"] <= 100


# ============================================================
# Dashboard Analytics Tests
# ============================================================
class TestDashboardAnalytics:
    """数据看板分析引擎测试"""

    def test_init(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        assert analytics is not None

    def test_get_selection_funnel(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        funnel = analytics.get_selection_funnel()
        assert funnel is not None
        assert isinstance(funnel, dict)

    def test_get_kpi_cards(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        kpis = analytics.get_kpi_cards()
        assert kpis is not None
        assert isinstance(kpis, list)

    def test_get_activity_trend(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        trend = analytics.get_activity_trend(days=7)
        assert trend is not None
        assert isinstance(trend, dict)

    def test_get_project_progress(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        progress = analytics.get_project_progress()
        assert progress is not None
        assert isinstance(progress, (list, dict))

    def test_get_profit_distribution(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        dist = analytics.get_profit_distribution()
        assert dist is not None
        assert isinstance(dist, dict)

    def test_get_full_dashboard(self):
        from analysis.dashboard_analytics import DashboardAnalytics
        analytics = DashboardAnalytics()
        dashboard = analytics.get_full_dashboard()
        assert dashboard is not None
        assert isinstance(dashboard, dict)


# ============================================================
# Pipeline Integration Tests (without OpenAI)
# ============================================================
class TestPipelineIntegration:
    """Pipeline 集成测试 - 验证新模块在 Pipeline 中的引用"""

    def test_pipeline_imports(self):
        """验证 amazon_pipeline 可以导入新模块"""
        from analysis.bsr_tracker import BSRTracker
        from analysis.competitor_finder import CompetitorFinder
        from analysis.sentiment_visualizer import SentimentVisualizer
        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        from analysis.dashboard_analytics import DashboardAnalytics
        assert BSRTracker is not None
        assert CompetitorFinder is not None
        assert SentimentVisualizer is not None
        assert ProductDecisionEngine is not None
        assert DashboardAnalytics is not None

    def test_new_modules_have_required_methods(self):
        """验证新模块有 Pipeline 调用所需的方法"""
        from analysis.bsr_tracker import BSRTracker
        tracker = BSRTracker()
        assert hasattr(tracker, "record_snapshot")
        assert hasattr(tracker, "batch_record")
        assert hasattr(tracker, "get_bsr_history")
        assert hasattr(tracker, "detect_anomalies")

        from analysis.competitor_finder import CompetitorFinder
        finder = CompetitorFinder()
        assert hasattr(finder, "find_by_keyword")
        assert hasattr(finder, "analyze_competitive_landscape")
        assert hasattr(finder, "build_comparison_matrix")

        from analysis.sentiment_visualizer import SentimentVisualizer
        viz = SentimentVisualizer()
        assert hasattr(viz, "generate_full_visualization")
        assert hasattr(viz, "extract_review_tags")

        from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
        engine = ProductDecisionEngine(ai_client=None)
        assert hasattr(engine, "evaluate_product")
        assert hasattr(engine, "batch_evaluate")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
