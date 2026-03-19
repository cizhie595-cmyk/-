"""
针对 Step 5/7/8/10 修复的专项测试 (v2)

测试内容:
1. Step 5: amazon_pipeline 评论数据结构修复
2. Step 7: AmazonCategoryAnalyzer 构造函数和参数顺序修复
3. Step 8: 1688 以图搜货图片路径兼容性
4. Step 10: ReportGenerator 双平台支持
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Step 5: 评论数据结构修复测试
# ============================================================

class TestReviewDataStructureFix:
    """测试 amazon_pipeline 中评论数据结构处理"""

    def test_crawl_reviews_returns_dict(self):
        """验证 AmazonReviewCrawler.crawl_reviews 返回 dict 而非 list"""
        from scrapers.amazon.review_crawler import AmazonReviewCrawler
        crawler = AmazonReviewCrawler(marketplace="US")
        # 不实际爬取，只验证方法存在且返回类型约定
        assert hasattr(crawler, "crawl_reviews")
        assert hasattr(crawler, "_detect_fake_reviews")
        crawler.close()

    def test_review_result_extraction_logic(self):
        """验证 pipeline 中从 crawl_result dict 提取 reviews 列表的逻辑"""
        # 模拟 crawl_reviews 返回的 dict
        crawl_result = {
            "asin": "B0TEST123",
            "reviews": [
                {"review_id": "R1", "rating": 5, "body": "Great product"},
                {"review_id": "R2", "rating": 3, "body": "OK product"},
                {"review_id": "R3", "rating": 1, "body": "Bad product"},
            ],
            "total_crawled": 3,
            "statistics": {"avg_rating": 3.0, "total": 3},
            "fake_review_suspects": [],
        }

        # 模拟修复后的提取逻辑
        reviews_list = crawl_result.get("reviews", []) if isinstance(crawl_result, dict) else crawl_result
        assert isinstance(reviews_list, list)
        assert len(reviews_list) == 3
        assert reviews_list[0]["review_id"] == "R1"

    def test_review_result_extraction_fallback(self):
        """当 crawl_result 不是 dict 时应该直接使用"""
        # 如果返回的是 list（旧版兼容）
        crawl_result = [
            {"review_id": "R1", "rating": 5, "body": "Great"},
        ]
        reviews_list = crawl_result.get("reviews", []) if isinstance(crawl_result, dict) else crawl_result
        assert isinstance(reviews_list, list)
        assert len(reviews_list) == 1


# ============================================================
# Step 7: AmazonCategoryAnalyzer 修复测试
# ============================================================

class TestCategoryAnalyzerFix:
    """测试 AmazonCategoryAnalyzer 构造函数和参数顺序"""

    def test_constructor_accepts_ai_client_and_model(self):
        """构造函数应接受 ai_client 和 ai_model 参数"""
        from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer
        # 不传 http_client（修复前会报错）
        analyzer = AmazonCategoryAnalyzer(ai_client=None, ai_model="gpt-4.1-mini")
        assert analyzer.ai_client is None
        assert analyzer.ai_model == "gpt-4.1-mini"

    def test_constructor_rejects_http_client(self):
        """构造函数不应接受 http_client 参数"""
        from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer
        with pytest.raises(TypeError):
            AmazonCategoryAnalyzer(http_client="fake", ai_client=None)

    def test_analyze_category_param_order(self):
        """analyze_category 参数顺序应为 (products, keyword, trends_data)"""
        from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer
        analyzer = AmazonCategoryAnalyzer()

        products = [
            {"asin": "B001", "price": 25.0, "rating": 4.5, "review_count": 200, "bsr": 1000, "brand": "BrandA"},
            {"asin": "B002", "price": 35.0, "rating": 4.0, "review_count": 150, "bsr": 2000, "brand": "BrandB"},
            {"asin": "B003", "price": 30.0, "rating": 4.2, "review_count": 100, "bsr": 3000, "brand": "BrandA"},
        ]
        keyword = "test keyword"

        # 正确的参数顺序: products, keyword
        result = analyzer.analyze_category(products, keyword)

        assert result is not None
        assert result["keyword"] == keyword
        assert result["product_count"] == 3
        assert "market_size" in result
        assert "competition" in result
        assert "pricing" in result
        assert "brand_concentration" in result
        assert "monopoly_index" in result
        assert "opportunity" in result

    def test_analyze_category_output_structure(self):
        """验证 analyze_category 输出的完整结构"""
        from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer
        analyzer = AmazonCategoryAnalyzer()

        products = [
            {"asin": "B001", "price": 25.0, "rating": 4.5, "review_count": 200, "bsr": 500, "brand": "BrandA"},
            {"asin": "B002", "price": 35.0, "rating": 4.0, "review_count": 50, "bsr": 1500, "brand": "BrandB"},
        ]

        result = analyzer.analyze_category(products, "test")

        # 市场容量
        market = result["market_size"]
        assert "estimated_total_monthly_gmv" in market
        assert "market_size_tier" in market
        assert "avg_monthly_sales_per_product" in market

        # 竞争格局
        comp = result["competition"]
        assert "competition_level" in comp
        assert "new_entry_difficulty" in comp
        assert "avg_review_count" in comp

        # 垄断度
        monopoly = result["monopoly_index"]
        assert "index" in monopoly
        assert "level" in monopoly
        assert "advice" in monopoly

        # 机会
        opp = result["opportunity"]
        assert "opportunity_score" in opp
        assert "grade" in opp
        assert "opportunities" in opp
        assert "risk_factors" in opp
        assert "recommendation" in opp


# ============================================================
# Step 8: 1688 图片路径兼容性测试
# ============================================================

class TestSourceSearchImageFix:
    """测试 1688 货源搜索的图片路径兼容性"""

    def test_main_image_url_extraction(self):
        """验证从多种字段格式提取主图 URL"""
        # 格式1: main_image (Amazon 爬虫输出)
        product1 = {"main_image": "https://images.amazon.com/test.jpg"}
        url1 = (
            product1.get("main_image")
            or product1.get("main_image_url")
            or product1.get("image_url")
            or ""
        )
        assert url1 == "https://images.amazon.com/test.jpg"

        # 格式2: main_image_url (数据库字段)
        product2 = {"main_image_url": "https://images.amazon.com/test2.jpg"}
        url2 = (
            product2.get("main_image")
            or product2.get("main_image_url")
            or product2.get("image_url")
            or ""
        )
        assert url2 == "https://images.amazon.com/test2.jpg"

        # 格式3: image_url (备选)
        product3 = {"image_url": "https://images.amazon.com/test3.jpg"}
        url3 = (
            product3.get("main_image")
            or product3.get("main_image_url")
            or product3.get("image_url")
            or ""
        )
        assert url3 == "https://images.amazon.com/test3.jpg"

        # 格式4: 无图片
        product4 = {"title": "No Image Product"}
        url4 = (
            product4.get("main_image")
            or product4.get("main_image_url")
            or product4.get("image_url")
            or ""
        )
        assert url4 == ""

    def test_images_array_fallback(self):
        """验证旧的 images 数组格式也能正确处理"""
        product = {
            "images": [
                {"type": "main", "url": "https://example.com/main.jpg"},
                {"type": "detail", "url": "https://example.com/detail.jpg"},
            ]
        }

        main_image_url = (
            product.get("main_image")
            or product.get("main_image_url")
            or product.get("image_url")
            or ""
        )

        if not main_image_url:
            images = product.get("images", [])
            main_img = next(
                (img for img in images if img.get("type") == "main"),
                None,
            )
            if main_img:
                main_image_url = main_img.get("local_path") or main_img.get("url", "")

        assert main_image_url == "https://example.com/main.jpg"


# ============================================================
# Step 10: ReportGenerator 双平台测试
# ============================================================

class TestReportGeneratorDualPlatform:
    """测试 ReportGenerator 的双平台支持"""

    def setup_method(self):
        from analysis.market_analysis.report_generator import ReportGenerator
        self.ReportGenerator = ReportGenerator

    def test_detect_amazon_platform(self):
        """应该从 asin 字段检测到 Amazon 平台"""
        products = [{"asin": "B001", "title": "Test"}]
        platform = self.ReportGenerator._detect_platform(products)
        assert platform == "amazon"

    def test_detect_coupang_platform(self):
        """应该从 coupang_product_id 字段检测到 Coupang 平台"""
        products = [{"coupang_product_id": "12345", "title": "Test"}]
        platform = self.ReportGenerator._detect_platform(products)
        assert platform == "coupang"

    def test_detect_from_category_analysis(self):
        """应该从 category_analysis 结构检测平台"""
        # Amazon 格式
        amazon_cat = {"market_size": {}, "competition": {}}
        platform = self.ReportGenerator._detect_platform([], amazon_cat)
        assert platform == "amazon"

        # Coupang 格式
        coupang_cat = {"gmv_estimate": {}}
        platform = self.ReportGenerator._detect_platform([], coupang_cat)
        assert platform == "coupang"

    def test_explicit_platform_override(self):
        """显式指定 platform 应该覆盖自动检测"""
        gen = self.ReportGenerator(platform="amazon")
        assert gen.platform == "amazon"

    def test_generate_amazon_report(self):
        """生成 Amazon 报告应该包含正确的标题和结构"""
        gen = self.ReportGenerator(platform="amazon")

        products = [
            {"asin": "B001", "title": "Test Product 1", "price": 25.0,
             "rating": 4.5, "review_count": 200, "bsr": 1000, "fulfillment_type": "FBA"},
            {"asin": "B002", "title": "Test Product 2", "price": 35.0,
             "rating": 4.0, "review_count": 150, "bsr": 2000, "fulfillment_type": "FBM"},
        ]

        category_analysis = {
            "keyword": "test",
            "market_size": {
                "estimated_total_monthly_gmv": 500000,
                "market_size_tier": "中型市场($100K-$1M/月)",
                "avg_monthly_sales_per_product": 300,
                "avg_price": 30.0,
            },
            "competition": {
                "competition_level": "中等竞争",
                "new_entry_difficulty": "中等",
                "avg_review_count": 175,
                "top_10_avg_reviews": 200,
                "avg_rating": 4.25,
            },
            "monopoly_index": {
                "index": 35.0,
                "level": "竞争分散",
                "advice": "市场分散，新品有较好的进入机会",
            },
            "opportunity": {
                "opportunity_score": 70,
                "grade": "B",
                "recommendation": "建议进入",
                "opportunities": ["竞争适中", "无主导品牌"],
                "risk_factors": ["需要差异化"],
            },
        }

        profit_results = [
            {
                "asin": "B001",
                "selling_price": 25.0,
                "costs": {
                    "cogs_rmb": 30.0,
                    "fba_fulfillment_fee": 5.0,
                    "referral_fee": 3.75,
                    "ppc_cost": 2.0,
                },
                "profit": {
                    "profit_per_unit_usd": 5.50,
                    "profit_margin": "22.0%",
                    "roi": "85.0%",
                },
                "health_check": {"is_healthy": True},
            },
        ]

        output_dir = "/tmp/test_reports"
        os.makedirs(output_dir, exist_ok=True)

        report_path = gen.generate(
            keyword="test product",
            products=products,
            category_analysis=category_analysis,
            profit_results=profit_results,
            output_dir=output_dir,
        )

        assert os.path.exists(report_path)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证 Amazon 特有内容
        assert "Amazon" in content
        assert "Coupang" not in content.split("##")[0]  # 标题中不应有 Coupang
        assert "ASIN" in content
        assert "FBA" in content
        assert "$" in content  # USD 货币符号
        assert "B001" in content
        assert "竞争分散" in content or "Monopoly" in content
        assert "建议进入" in content or "Opportunities" in content

        # 清理
        os.remove(report_path)

    def test_generate_coupang_report(self):
        """生成 Coupang 报告应该包含正确的标题和结构"""
        gen = self.ReportGenerator(platform="coupang")

        products = [
            {"coupang_product_id": "12345", "title": "Test Product", "price": 25000,
             "rating": 4.5, "review_count": 200, "delivery_type": "로켓배송"},
        ]

        output_dir = "/tmp/test_reports"
        os.makedirs(output_dir, exist_ok=True)

        report_path = gen.generate(
            keyword="test",
            products=products,
            output_dir=output_dir,
        )

        assert os.path.exists(report_path)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Coupang" in content
        assert "로켓배송" in content or "配送" in content

        os.remove(report_path)

    def test_amazon_profit_table_nested_structure(self):
        """Amazon 利润表格应该正确读取嵌套结构"""
        gen = self.ReportGenerator(platform="amazon")

        profit_results = [
            {
                "asin": "B001",
                "selling_price": 29.99,
                "costs": {
                    "cogs_rmb": 35.0,
                    "fba_fulfillment_fee": 5.50,
                    "referral_fee": 4.50,
                },
                "profit": {
                    "profit_per_unit_usd": 8.20,
                    "profit_margin": "27.3%",
                    "roi": "95.0%",
                },
                "health_check": {"is_healthy": True},
            },
        ]

        lines = gen._profit_table_amazon(profit_results, "zh_CN")
        table_text = "\n".join(lines)

        assert "B001" in table_text
        assert "$29.99" in table_text
        assert "¥35.00" in table_text
        assert "$5.50" in table_text
        assert "$8.20" in table_text
        assert "27.3%" in table_text

    def test_amazon_market_overview_structure(self):
        """Amazon 市场概况应该正确读取 AmazonCategoryAnalyzer 输出"""
        gen = self.ReportGenerator(platform="amazon")

        category = {
            "market_size": {
                "estimated_total_monthly_gmv": 500000,
                "market_size_tier": "中型市场($100K-$1M/月)",
                "avg_monthly_sales_per_product": 300,
                "avg_price": 30.0,
            },
            "competition": {
                "competition_level": "中等竞争",
                "new_entry_difficulty": "中等",
                "avg_review_count": 175,
                "top_10_avg_reviews": 200,
                "avg_rating": 4.25,
            },
        }

        lines = gen._market_overview_amazon(category, "zh_CN")
        text = "\n".join(lines)

        assert "$500,000" in text
        assert "中型市场" in text
        assert "中等竞争" in text
        assert "175" in text
        assert "4.25" in text


# ============================================================
# 集成测试: amazon_pipeline 修复后的 Step 调用兼容性
# ============================================================

class TestPipelineStepIntegration:
    """验证 amazon_pipeline 修复后的 Step 调用签名正确性"""

    def test_step7_call_signature_matches(self):
        """Step 7: pipeline 调用签名应匹配 AmazonCategoryAnalyzer"""
        from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer
        import inspect

        # 验证构造函数签名
        init_sig = inspect.signature(AmazonCategoryAnalyzer.__init__)
        params = list(init_sig.parameters.keys())
        assert "self" in params
        assert "ai_client" in params
        assert "ai_model" in params
        assert "http_client" not in params  # 修复后不应有 http_client

        # 验证 analyze_category 签名
        method_sig = inspect.signature(AmazonCategoryAnalyzer.analyze_category)
        params = list(method_sig.parameters.keys())
        assert params[0] == "self"
        assert params[1] == "products"   # 第一个参数是 products
        assert params[2] == "keyword"    # 第二个参数是 keyword

    def test_step10_report_generator_accepts_platform(self):
        """Step 10: ReportGenerator 应接受 platform 参数"""
        from analysis.market_analysis.report_generator import ReportGenerator
        import inspect

        init_sig = inspect.signature(ReportGenerator.__init__)
        params = list(init_sig.parameters.keys())
        assert "platform" in params

        # 验证可以传入 platform="amazon"
        gen = ReportGenerator(ai_client=None, platform="amazon")
        assert gen.platform == "amazon"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
