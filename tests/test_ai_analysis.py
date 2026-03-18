"""
AI 分析模块 Mock 测试
Issue #12: 提升测试覆盖率 - AI 分析模块
使用 unittest.mock 模拟 OpenAI API 调用，测试分析逻辑
"""
import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Data Filter Tests
# ============================================================
class TestDataFilter(unittest.TestCase):
    """数据筛选器测试"""

    def setUp(self):
        from analysis.data_filter import DataFilter
        self.filter = DataFilter()

    def test_init_default_rules(self):
        """测试默认规则初始化"""
        self.assertIsNotNone(self.filter)

    def test_filter_products_empty_list(self):
        """测试空列表筛选"""
        result = self.filter.filter_products([])
        self.assertIsInstance(result, dict)
        self.assertIn("kept", result)
        self.assertEqual(len(result["kept"]), 0)

    def test_filter_products_with_data(self):
        """测试有数据的筛选"""
        products = [
            {
                "asin": "B0TEST001",
                "title": "Test Product 1",
                "price": 29.99,
                "reviews": 500,
                "rating": 4.5,
                "monthly_sales": 1000,
            },
            {
                "asin": "B0TEST002",
                "title": "Test Product 2",
                "price": 9.99,
                "reviews": 10,
                "rating": 3.0,
                "monthly_sales": 50,
            },
        ]
        result = self.filter.filter_products(products)
        self.assertIsInstance(result, dict)
        self.assertIn("kept", result)
        self.assertIn("filtered", result)

    def test_filter_with_custom_rules(self):
        """测试自定义规则筛选"""
        from analysis.data_filter import DataFilter
        custom_rules = {
            "min_price": 20.0,
            "max_price": 100.0,
            "min_reviews": 100,
            "min_rating": 4.0,
        }
        f = DataFilter(rules=custom_rules)
        products = [
            {"asin": "B001", "price": 50.0, "reviews": 200, "rating": 4.5},
            {"asin": "B002", "price": 5.0, "reviews": 5, "rating": 2.0},
        ]
        result = f.filter_products(products)
        self.assertIsInstance(result, dict)


# ============================================================
# Amazon Data Filter Tests
# ============================================================
class TestAmazonDataFilter(unittest.TestCase):
    """Amazon 数据筛选器测试"""

    def setUp(self):
        from analysis.amazon_data_filter import AmazonDataFilter
        self.filter = AmazonDataFilter()

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.filter)

    def test_filter_products_empty(self):
        """测试空列表"""
        result = self.filter.filter_products([])
        self.assertIsInstance(result, dict)

    def test_filter_products_with_amazon_data(self):
        """测试 Amazon 格式数据筛选"""
        products = [
            {
                "asin": "B0TEST001",
                "title": "Wireless Earbuds",
                "price": 39.99,
                "reviews_count": 2345,
                "rating": 4.3,
                "bsr": 5000,
                "category": "Electronics",
                "seller_count": 3,
                "monthly_revenue": 50000,
            }
        ]
        result = self.filter.filter_products(products)
        self.assertIsInstance(result, dict)

    def test_apply_amazon_rules(self):
        """测试 Amazon 特定规则"""
        product = {
            "asin": "B0TEST001",
            "price": 25.0,
            "reviews_count": 100,
            "rating": 4.0,
            "bsr": 10000,
        }
        passed, reasons = self.filter._apply_amazon_rules(product)
        self.assertIsInstance(passed, bool)
        self.assertIsInstance(reasons, list)


# ============================================================
# Detail Page Analyzer Tests (AI Mock)
# ============================================================
class TestDetailPageAnalyzer(unittest.TestCase):
    """详情页 AI 分析器测试"""

    def setUp(self):
        from analysis.ai_analysis.detail_analyzer import DetailPageAnalyzer
        self.mock_ai = MagicMock()
        self.analyzer = DetailPageAnalyzer(ai_client=self.mock_ai)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.analyzer)

    def test_analyze_with_mock_ai(self):
        """测试 AI 分析（Mock OpenAI）"""
        # Mock AI 返回
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "quality_score": 8,
            "listing_quality": "good",
            "image_quality": "high",
            "bullet_points_analysis": "Well structured",
            "competitive_advantages": ["Good price", "Fast shipping"],
            "improvement_suggestions": ["Add more images"],
        })
        self.mock_ai.chat.completions.create.return_value = mock_response

        product_data = {
            "asin": "B0TEST001",
            "title": "Test Product",
            "price": 29.99,
            "bullet_points": ["Feature 1", "Feature 2"],
            "images": ["https://example.com/img1.jpg"],
        }
        result = self.analyzer.analyze(product_data)
        self.assertIsInstance(result, dict)


# ============================================================
# Review Analyzer Tests (AI Mock)
# ============================================================
class TestReviewAnalyzer(unittest.TestCase):
    """评论分析器测试"""

    def setUp(self):
        from analysis.ai_analysis.review_analyzer import ReviewAnalyzer
        self.mock_ai = MagicMock()
        self.analyzer = ReviewAnalyzer(ai_client=self.mock_ai)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.analyzer)

    def test_analyze_empty_reviews(self):
        """测试空评论分析"""
        result = self.analyzer.analyze([], product_title="Test")
        self.assertIsInstance(result, dict)

    def test_analyze_with_reviews(self):
        """测试有评论的分析"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_sentiment": "positive",
            "sentiment_score": 0.85,
            "key_positives": ["Good quality", "Fast delivery"],
            "key_negatives": ["Battery life could be better"],
            "common_themes": ["sound quality", "comfort"],
        })
        self.mock_ai.chat.completions.create.return_value = mock_response

        reviews = [
            {"title": "Great product!", "body": "Love the sound quality", "rating": 5},
            {"title": "Good value", "body": "Works well for the price", "rating": 4},
            {"title": "Decent", "body": "Battery could be better", "rating": 3},
        ]
        result = self.analyzer.analyze(reviews, product_title="Wireless Earbuds")
        self.assertIsInstance(result, dict)


# ============================================================
# Risk Analyzer Tests (AI Mock)
# ============================================================
class TestRiskAnalyzer(unittest.TestCase):
    """风险分析器测试"""

    def setUp(self):
        from analysis.ai_analysis.risk_analyzer import RiskAnalyzer
        self.mock_ai = MagicMock()
        self.analyzer = RiskAnalyzer(ai_client=self.mock_ai)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.analyzer)

    def test_analyze_risks(self):
        """测试风险分析（Mock AI）"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "competition_risk": 6,
            "demand_risk": 3,
            "profit_risk": 4,
            "ip_risk": 2,
            "seasonality_risk": 5,
            "overall_risk": 4,
            "risk_summary": "Moderate risk product",
            "recommendations": ["Monitor competition", "Diversify suppliers"],
        })
        self.mock_ai.chat.completions.create.return_value = mock_response

        product_data = {
            "asin": "B0TEST001",
            "title": "Test Product",
            "price": 29.99,
            "reviews_count": 500,
            "rating": 4.2,
            "bsr": 5000,
            "category": "Electronics",
            "seller_count": 5,
        }
        result = self.analyzer.analyze_risks(product_data)
        self.assertIsInstance(result, dict)


# ============================================================
# Category Analyzer Tests
# ============================================================
class TestCategoryAnalyzer(unittest.TestCase):
    """品类分析器测试"""

    def setUp(self):
        from analysis.market_analysis.category_analyzer import CategoryAnalyzer
        self.mock_http = MagicMock()
        self.mock_ai = MagicMock()
        self.analyzer = CategoryAnalyzer(http_client=self.mock_http, ai_client=self.mock_ai)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.analyzer)

    def test_analyze_category(self):
        """测试品类分析"""
        products = [
            {"asin": "B001", "price": 20.0, "reviews_count": 100, "rating": 4.0, "bsr": 5000},
            {"asin": "B002", "price": 30.0, "reviews_count": 200, "rating": 4.5, "bsr": 3000},
            {"asin": "B003", "price": 40.0, "reviews_count": 300, "rating": 3.8, "bsr": 8000},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "market_size": "medium",
            "competition_level": "high",
            "entry_barrier": "medium",
            "growth_trend": "stable",
        })
        self.mock_ai.chat.completions.create.return_value = mock_response

        result = self.analyzer.analyze_category("wireless earbuds", products)
        self.assertIsInstance(result, dict)


# ============================================================
# Report Generator Tests
# ============================================================
class TestReportGenerator(unittest.TestCase):
    """报告生成器测试"""

    def setUp(self):
        from analysis.market_analysis.report_generator import ReportGenerator
        self.mock_ai = MagicMock()
        self.generator = ReportGenerator(ai_client=self.mock_ai)

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.generator)

    def test_generate_report(self):
        """测试报告生成"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# Market Report\n\n## Summary\nThis is a test report."
        self.mock_ai.chat.completions.create.return_value = mock_response

        products = [
            {"asin": "B001", "title": "Product 1", "price": 29.99, "reviews_count": 500},
        ]
        result = self.generator.generate("wireless earbuds", products)
        self.assertIsInstance(result, (str, dict))


# ============================================================
# Profit Calculator Tests
# ============================================================
class TestProfitCalculator(unittest.TestCase):
    """利润计算器测试"""

    def setUp(self):
        from analysis.profit_analysis.profit_calculator import ProfitCalculator
        self.calc = ProfitCalculator()

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.calc)

    def test_calculate_profit(self):
        """测试利润计算"""
        result = self.calc.calculate(
            selling_price_krw=35000,
            source_data={"unit_price_cny": 30, "shipping_cny": 5},
        )
        self.assertIsInstance(result, dict)
        if "profit" in result:
            self.assertIsInstance(result["profit"], (int, float))


# ============================================================
# Amazon FBA Profit Calculator Tests
# ============================================================
class TestAmazonFBAProfitCalculator(unittest.TestCase):
    """Amazon FBA 利润计算器测试"""

    def setUp(self):
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator
        self.calc = AmazonFBAProfitCalculator(marketplace="US")

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.calc.marketplace, "US")

    def test_calculate_profit(self):
        """测试 FBA 利润计算"""
        params = {
            "selling_price": 29.99,
            "product_cost": 5.0,
            "shipping_to_fba": 3.0,
            "weight_lb": 0.5,
            "length": 10,
            "width": 8,
            "height": 4,
            "category": "Electronics",
        }
        result = self.calc.calculate_profit(params)
        self.assertIsInstance(result, dict)
        if "net_profit" in result:
            self.assertIsInstance(result["net_profit"], (int, float))
        if "roi" in result:
            self.assertIsInstance(result["roi"], (int, float))


# ============================================================
# Data Exporter Tests
# ============================================================
class TestDataExporter(unittest.TestCase):
    """数据导出器测试"""

    def test_export_csv(self):
        """测试 CSV 导出"""
        from utils.data_exporter import DataExporter
        data = [
            {"asin": "B001", "title": "Product 1", "price": 29.99},
            {"asin": "B002", "title": "Product 2", "price": 39.99},
        ]
        result = DataExporter.export_csv(data)
        self.assertIsNotNone(result)

    def test_export_csv_empty(self):
        """测试空数据 CSV 导出"""
        from utils.data_exporter import DataExporter
        result = DataExporter.export_csv([])
        self.assertIsNotNone(result)

    def test_export_excel(self):
        """测试 Excel 导出"""
        from utils.data_exporter import DataExporter
        data = [
            {"asin": "B001", "title": "Product 1", "price": 29.99},
        ]
        result = DataExporter.export_excel(data)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestDataFilter,
        TestAmazonDataFilter,
        TestDetailPageAnalyzer,
        TestReviewAnalyzer,
        TestRiskAnalyzer,
        TestCategoryAnalyzer,
        TestReportGenerator,
        TestProfitCalculator,
        TestAmazonFBAProfitCalculator,
        TestDataExporter,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n{'='*60}")
    print(f"AI Analysis Tests: {result.testsRun} run, "
          f"{len(result.failures)} failures, "
          f"{len(result.errors)} errors, "
          f"{len(result.skipped)} skipped")
    print(f"{'='*60}")

    sys.exit(0 if result.wasSuccessful() else 1)
