"""
测试新开发的 4 个模块：
- Step 2: CompetitorTracker (竞品监控追踪器)
- Step 3: KeywordResearcher (关键词研究工具)
- Step 8: SupplierScorer (供应商评分系统)
- Step 9: PricingOptimizer (定价策略优化器)
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Step 2: CompetitorTracker Tests
# ============================================================
class TestCompetitorTracker:
    def setup_method(self):
        from analysis.competitor_tracker import CompetitorTracker
        self.tracker = CompetitorTracker()

    def test_init(self):
        """验证核心方法存在"""
        assert hasattr(self.tracker, 'take_snapshot')
        assert hasattr(self.tracker, 'detect_changes')
        assert hasattr(self.tracker, 'get_trend_data')
        assert hasattr(self.tracker, 'generate_comparison_matrix')
        assert hasattr(self.tracker, 'batch_snapshot')

    def test_take_snapshot_without_db(self):
        """无数据库时 take_snapshot 应返回空 dict"""
        result = self.tracker.take_snapshot("B0XXXXXXXXX")
        assert isinstance(result, dict)

    def test_detect_changes_without_db(self):
        """无数据库时 detect_changes 应返回空列表"""
        alerts = self.tracker.detect_changes(monitor_id=1)
        assert isinstance(alerts, list)
        assert len(alerts) == 0

    def test_get_trend_data_without_db(self):
        """无数据库时 get_trend_data 应返回结构化空数据"""
        trend = self.tracker.get_trend_data(monitor_id=1, days=30, metric="price")
        assert "labels" in trend
        assert "values" in trend
        assert "metric" in trend
        assert trend["metric"] == "price"
        assert len(trend["labels"]) == 0

    def test_get_trend_data_invalid_metric(self):
        """无效指标应回退到 price"""
        trend = self.tracker.get_trend_data(monitor_id=1, metric="invalid_metric")
        assert trend["metric"] == "price"

    def test_generate_comparison_matrix_without_db(self):
        """无数据库时 generate_comparison_matrix 应返回空结构"""
        result = self.tracker.generate_comparison_matrix(user_id=1, project_id=1)
        assert isinstance(result, dict)

    def test_default_alert_thresholds(self):
        """验证默认告警阈值配置"""
        assert hasattr(self.tracker, 'DEFAULT_ALERT_THRESHOLDS')
        thresholds = self.tracker.DEFAULT_ALERT_THRESHOLDS
        assert "price_drop_pct" in thresholds
        assert "bsr_improve_pct" in thresholds


# ============================================================
# Step 3: KeywordResearcher Tests
# ============================================================
class TestKeywordResearcher:
    def setup_method(self):
        from analysis.keyword_researcher import KeywordResearcher
        self.researcher = KeywordResearcher()

    def test_init(self):
        assert hasattr(self.researcher, 'assess_keyword_difficulty')
        assert hasattr(self.researcher, 'estimate_search_volume')
        assert hasattr(self.researcher, 'generate_long_tail_keywords')
        assert hasattr(self.researcher, 'get_autocomplete_suggestions')
        assert hasattr(self.researcher, 'full_research')

    def test_analyze_difficulty_low(self):
        products = [
            {"review_count": 50, "rating": 4.0, "bsr_rank": 50000, "fulfillment": "MFN", "price": 25.00}
            for _ in range(10)
        ]
        result = self.researcher.assess_keyword_difficulty("test keyword", products)
        assert "difficulty_score" in result
        assert "difficulty_level" in result
        assert "factors" in result
        assert 0 <= result["difficulty_score"] <= 100

    def test_analyze_difficulty_high(self):
        products = [
            {"review_count": 5000, "rating": 4.8, "bsr_rank": 100, "fulfillment": "FBA", "price": 25.00,
             "brand": f"Brand{i}"}
            for i in range(10)
        ]
        result = self.researcher.assess_keyword_difficulty("test keyword", products)
        assert result["difficulty_score"] > 50

    def test_estimate_search_volume(self):
        products = [
            {"review_count": 500, "bsr_rank": 1000, "price": 25.00}
            for _ in range(10)
        ]
        result = self.researcher.estimate_search_volume("wireless earbuds", products)
        assert "estimated_monthly_searches" in result
        assert "confidence" in result
        assert result["estimated_monthly_searches"] > 0

    def test_generate_long_tail_keywords(self):
        keywords = self.researcher.generate_long_tail_keywords("wireless earbuds")
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        for kw in keywords:
            assert "keyword" in kw
            assert "category" in kw

    def test_generate_long_tail_categories(self):
        keywords = self.researcher.generate_long_tail_keywords("yoga mat")
        categories = set(kw["category"] for kw in keywords)
        assert len(categories) >= 2

    def test_get_autocomplete_suggestions(self):
        suggestions = self.researcher.get_autocomplete_suggestions("wireless earbuds")
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_full_research_pipeline(self):
        products = [
            {"review_count": 200, "rating": 4.3, "bsr_rank": 5000, "fulfillment": "FBA", "price": 30.00}
            for _ in range(10)
        ]
        result = self.researcher.full_research("test product", products)
        assert "difficulty_analysis" in result
        assert "volume_analysis" in result
        assert "keywords" in result
        assert "summary" in result


# ============================================================
# Step 8: SupplierScorer Tests
# ============================================================
class TestSupplierScorer:
    def setup_method(self):
        from analysis.supplier_scorer import SupplierScorer
        self.scorer = SupplierScorer()

    def test_init(self):
        assert hasattr(self.scorer, 'score_supplier')
        assert hasattr(self.scorer, 'score_multiple_suppliers')
        assert hasattr(self.scorer, 'generate_comparison_matrix')
        assert hasattr(self.scorer, 'score_credibility')
        assert hasattr(self.scorer, 'score_product_capability')
        assert hasattr(self.scorer, 'score_service_quality')
        assert hasattr(self.scorer, 'score_price_competitiveness')
        assert hasattr(self.scorer, 'score_logistics')

    def test_score_credibility(self):
        supplier = {"business_years": 8, "trade_assurance": True, "transaction_count": 5000,
                     "repeat_purchase_rate": 0.35}
        result = self.scorer.score_credibility(supplier)
        assert "score" in result
        assert "details" in result
        assert 0 <= result["score"] <= 100

    def test_score_product_capability(self):
        supplier = {"certifications": ["ISO9001", "CE"], "oem": True, "odm": True,
                     "sample_available": True}
        result = self.scorer.score_product_capability(supplier)
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_score_service_quality(self):
        supplier = {"response_time": "1小时内", "moq": "100", "sample_available": True}
        result = self.scorer.score_service_quality(supplier)
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_score_price_competitiveness(self):
        supplier = {"price": 20.00}
        result = self.scorer.score_price_competitiveness(supplier, market_avg_price=30.00)
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_score_logistics(self):
        supplier = {"lead_time": 5, "shipping_methods": ["海运", "空运"]}
        result = self.scorer.score_logistics(supplier)
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_score_supplier_full(self):
        supplier = {
            "name": "测试供应商",
            "business_years": 5,
            "trade_assurance": True,
            "certifications": ["ISO9001"],
            "oem": True,
            "price": 25.00,
        }
        result = self.scorer.score_supplier(supplier, market_avg_price=30.00)
        assert "total_score" in result
        assert "grade" in result
        assert "dimensions" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert "recommendation" in result
        assert result["grade"] in ["S", "A", "B", "C", "D"]

    def test_score_multiple_suppliers(self):
        suppliers = [
            {"name": "供应商A", "business_years": 5, "price": 20.00, "certifications": ["ISO9001"]},
            {"name": "供应商B", "business_years": 3, "price": 25.00, "certifications": []},
            {"name": "供应商C", "business_years": 8, "price": 22.00, "certifications": ["ISO9001", "CE"]},
        ]
        results = self.scorer.score_multiple_suppliers(suppliers, market_avg_price=25.00)
        assert len(results) == 3
        for r in results:
            assert "total_score" in r
            assert "grade" in r

    def test_generate_comparison_matrix(self):
        suppliers = [
            {"name": "供应商A", "business_years": 5, "price": 20.00, "certifications": ["ISO9001"]},
            {"name": "供应商B", "business_years": 3, "price": 25.00, "certifications": []},
        ]
        matrix = self.scorer.generate_comparison_matrix(suppliers, market_avg_price=25.00)
        assert isinstance(matrix, dict)
        assert "dimension_comparison" in matrix
        assert "best_in_class" in matrix
        assert "insights" in matrix


# ============================================================
# Step 9: PricingOptimizer Tests
# ============================================================
class TestPricingOptimizer:
    def setup_method(self):
        from analysis.pricing_optimizer import PricingOptimizer
        self.optimizer = PricingOptimizer()

    def test_init(self):
        assert hasattr(self.optimizer, 'suggest_optimal_price')
        assert hasattr(self.optimizer, 'simulate_price_elasticity')
        assert hasattr(self.optimizer, 'compare_strategies')
        assert hasattr(self.optimizer, 'analyze_price_distribution')
        assert hasattr(self.optimizer, 'suggest_promotions')

    def test_analyze_price_distribution(self):
        products = [
            {"price": 24.99}, {"price": 29.99}, {"price": 19.99},
            {"price": 27.50}, {"price": 22.99}, {"price": 31.00}, {"price": 26.50}
        ]
        result = self.optimizer.analyze_price_distribution(products)
        assert "statistics" in result
        stats = result["statistics"]
        assert "avg" in stats
        assert "median" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["min"] <= stats["avg"] <= stats["max"]

    def test_suggest_optimal_price(self):
        cost_params = {
            "sourcing_cost_rmb": 50.00,
            "shipping_cost_per_kg": 20.00,
            "weight_kg": 0.5,
        }
        products = [
            {"price": 24.99}, {"price": 29.99}, {"price": 19.99}, {"price": 27.50}
        ]
        result = self.optimizer.suggest_optimal_price(cost_params, products, target_margin=0.25)
        assert "optimal_price" in result
        assert "breakeven_price" in result
        assert "price_floor" in result
        assert "price_ceiling" in result
        assert "recommended_strategy" in result
        assert "cost_breakdown" in result
        assert "profit_at_optimal" in result
        assert result["optimal_price"] > 0
        assert result["breakeven_price"] > 0

    def test_breakeven_price_logic(self):
        cost_params = {
            "sourcing_cost_rmb": 72.50,  # 10 USD at 7.25 rate
            "shipping_cost_per_kg": 0,
            "weight_kg": 0,
            "fba_fee": 5.00,
        }
        products = [{"price": 25.00}, {"price": 30.00}]
        result = self.optimizer.suggest_optimal_price(cost_params, products, target_margin=0.20)
        # Breakeven should be > total_cost + fba_fee
        assert result["breakeven_price"] > 15.0

    def test_strategies_in_result(self):
        cost_params = {"sourcing_cost_rmb": 50.00, "shipping_cost_per_kg": 20.00, "weight_kg": 0.5}
        products = [{"price": 24.99}, {"price": 29.99}, {"price": 19.99}]
        result = self.optimizer.suggest_optimal_price(cost_params, products, target_margin=0.25)
        assert "recommended_strategy" in result
        assert result["recommended_strategy"] in ["penetration", "competitive", "value", "premium", "skimming"]

    def test_simulate_price_elasticity(self):
        cost_params = {"sourcing_cost_rmb": 50.00, "shipping_cost_per_kg": 20.00, "weight_kg": 0.5}
        products = [{"price": 24.99}, {"price": 29.99}, {"price": 19.99}, {"price": 27.50}]
        result = self.optimizer.simulate_price_elasticity(cost_params, products)
        assert "simulations" in result
        assert "elasticity_coefficient" in result
        assert "chart_data" in result
        assert len(result["simulations"]) > 0
        for sim in result["simulations"]:
            assert "price" in sim
            assert "profit_per_unit" in sim
            assert "monthly_profit" in sim

    def test_compare_strategies(self):
        cost_params = {"sourcing_cost_rmb": 50.00, "shipping_cost_per_kg": 20.00, "weight_kg": 0.5}
        products = [{"price": 24.99}, {"price": 29.99}, {"price": 19.99}]
        result = self.optimizer.compare_strategies(cost_params, products)
        assert "comparisons" in result
        assert "recommended_strategy" in result
        assert "chart_data" in result
        assert len(result["comparisons"]) >= 3

    def test_no_products(self):
        cost_params = {"sourcing_cost_rmb": 50.00, "shipping_cost_per_kg": 20.00, "weight_kg": 0.5}
        result = self.optimizer.suggest_optimal_price(cost_params, [], target_margin=0.25)
        assert "optimal_price" in result
        assert result["optimal_price"] > 0


# ============================================================
# Integration: Module Import Tests
# ============================================================
class TestModuleImports:
    def test_import_competitor_tracker(self):
        from analysis.competitor_tracker import CompetitorTracker
        assert CompetitorTracker is not None

    def test_import_keyword_researcher(self):
        from analysis.keyword_researcher import KeywordResearcher
        assert KeywordResearcher is not None

    def test_import_supplier_scorer(self):
        from analysis.supplier_scorer import SupplierScorer
        assert SupplierScorer is not None

    def test_import_pricing_optimizer(self):
        from analysis.pricing_optimizer import PricingOptimizer
        assert PricingOptimizer is not None

    def test_import_api_routes(self):
        """Verify all API route modules can be parsed"""
        import ast
        for route_file in [
            "api/competitor_routes.py",
            "api/keyword_routes.py",
            "api/supplier_routes.py",
            "api/pricing_routes.py",
        ]:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), route_file)
            with open(path) as f:
                ast.parse(f.read())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
