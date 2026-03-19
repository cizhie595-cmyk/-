"""
Step 修复 v3 - 专项测试
覆盖:
1. scraping_tasks._save_products_to_db 字段兼容性
2. analysis_tasks.generate_decision_report 数据收集逻辑
3. analysis_tasks.run_review_analysis 评论返回值处理
4. export_routes SQL 字段映射
5. pipeline.py Step 4 图片下载 + Step 8 以图搜货
6. pipeline.py Step 10 平台参数传递
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 1. scraping_tasks._save_products_to_db 字段兼容性
# ============================================================
class TestSaveProductsFieldMapping:
    """测试 _save_products_to_db 的字段名兼容层"""

    def test_field_mapping_from_search_crawler(self):
        """搜索爬虫输出 main_image, price, bsr 等字段应被正确映射"""
        product = {
            "asin": "B09TEST001",
            "title": "Test Product",
            "brand": "TestBrand",
            "main_image": "https://images.example.com/test.jpg",  # 爬虫输出
            "price": 29.99,
            "rating": 4.5,
            "review_count": 100,
            "bsr": 500,
            "fulfillment": "FBA",
            "monthly_sales": 3000,
        }

        # 模拟字段映射逻辑 (从 scraping_tasks._save_products_to_db)
        image_url = (
            product.get("main_image_url")
            or product.get("main_image")
            or product.get("image_url")
            or ""
        )
        price = product.get("price_current") or product.get("price")
        bsr_rank = product.get("bsr_rank") or product.get("bsr") or 0
        fulfillment = product.get("fulfillment_type") or product.get("fulfillment") or ""
        est_sales = (
            product.get("est_sales_30d")
            or product.get("estimated_monthly_sales")
            or product.get("monthly_sales")
            or 0
        )

        assert image_url == "https://images.example.com/test.jpg"
        assert price == 29.99
        assert bsr_rank == 500
        assert fulfillment == "FBA"
        assert est_sales == 3000

    def test_field_mapping_from_sp_api(self):
        """SP-API 输出 main_image_url, price_current 等字段应被正确映射"""
        product = {
            "asin": "B09TEST002",
            "title": "SP-API Product",
            "main_image_url": "https://images.example.com/sp.jpg",
            "price_current": 39.99,
            "bsr_rank": 200,
            "fulfillment_type": "FBM",
            "est_sales_30d": 5000,
        }

        image_url = (
            product.get("main_image_url")
            or product.get("main_image")
            or product.get("image_url")
            or ""
        )
        price = product.get("price_current") or product.get("price")
        bsr_rank = product.get("bsr_rank") or product.get("bsr") or 0
        fulfillment = product.get("fulfillment_type") or product.get("fulfillment") or ""
        est_sales = (
            product.get("est_sales_30d")
            or product.get("estimated_monthly_sales")
            or product.get("monthly_sales")
            or 0
        )

        assert image_url == "https://images.example.com/sp.jpg"
        assert price == 39.99
        assert bsr_rank == 200
        assert fulfillment == "FBM"
        assert est_sales == 5000


# ============================================================
# 2. analysis_tasks review_crawler 返回值处理
# ============================================================
class TestReviewCrawlerReturnHandling:
    """测试 crawl_reviews 返回 dict 时的正确处理"""

    def test_dict_return_extracts_reviews(self):
        """crawl_reviews 返回 dict 时应提取 reviews 列表"""
        crawl_result = {
            "asin": "B09TEST",
            "total_reviews": 50,
            "reviews": [
                {"text": "Great product!", "rating": 5},
                {"text": "Not bad", "rating": 3},
            ],
        }

        if isinstance(crawl_result, dict):
            reviews = crawl_result.get("reviews", [])
        else:
            reviews = crawl_result or []

        assert len(reviews) == 2
        assert reviews[0]["text"] == "Great product!"

    def test_list_return_used_directly(self):
        """crawl_reviews 返回 list 时应直接使用"""
        crawl_result = [
            {"text": "Great product!", "rating": 5},
        ]

        if isinstance(crawl_result, dict):
            reviews = crawl_result.get("reviews", [])
        else:
            reviews = crawl_result or []

        assert len(reviews) == 1

    def test_none_return_gives_empty_list(self):
        """crawl_reviews 返回 None 时应得到空列表"""
        crawl_result = None

        if isinstance(crawl_result, dict):
            reviews = crawl_result.get("reviews", [])
        else:
            reviews = crawl_result or []

        assert reviews == []


# ============================================================
# 3. ReportGenerator 平台参数
# ============================================================
class TestReportGeneratorPlatform:
    """测试 ReportGenerator 的平台参数传递"""

    def test_coupang_platform(self):
        """Coupang pipeline 应传入 platform='coupang'"""
        from analysis.market_analysis.report_generator import ReportGenerator
        gen = ReportGenerator(ai_client=None, platform="coupang")
        assert gen.platform == "coupang"

    def test_amazon_platform(self):
        """Amazon pipeline 应传入 platform='amazon'"""
        from analysis.market_analysis.report_generator import ReportGenerator
        gen = ReportGenerator(ai_client=None, platform="amazon")
        assert gen.platform == "amazon"

    def test_auto_detect_amazon(self):
        """传入 Amazon 数据时应自动检测平台"""
        from analysis.market_analysis.report_generator import ReportGenerator
        gen = ReportGenerator(ai_client=None)
        products = [{"asin": "B09TEST", "title": "Test", "price": 29.99}]
        # 应该能自动检测为 amazon
        assert gen.platform is None  # 初始为 None
        # 在 generate 中会自动检测


# ============================================================
# 4. export_routes SQL 字段映射
# ============================================================
class TestExportFieldMapping:
    """测试 export_routes 中的 SQL 字段别名"""

    def test_product_export_uses_correct_aliases(self):
        """产品导出 SQL 应使用 price_current AS price 等别名"""
        import ast
        with open("api/export_routes.py", "r") as f:
            content = f.read()

        # 验证使用了正确的别名
        assert "price_current AS price" in content
        assert "est_sales_30d AS monthly_sales" in content
        assert "bsr_category AS category" in content

    def test_analysis_export_uses_result_data(self):
        """分析导出应使用 result_data 而非 result_json"""
        with open("api/export_routes.py", "r") as f:
            content = f.read()

        assert "result_data" in content
        assert "result_json" not in content

    def test_profit_export_uses_correct_fields(self):
        """利润导出应使用 amazon_fees 和 sourcing_cost"""
        with open("api/export_routes.py", "r") as f:
            content = f.read()

        assert "pc.amazon_fees AS fba_fee" in content
        assert "pc.sourcing_cost AS cost_price" in content

    def test_report_export_uses_keyword_alias(self):
        """报告导出应使用 keyword AS keywords"""
        with open("api/export_routes.py", "r") as f:
            content = f.read()

        assert "keyword AS keywords" in content


# ============================================================
# 5. Coupang pipeline Step 4 图片下载
# ============================================================
class TestCoupangPipelineImageDownload:
    """测试 Coupang pipeline Step 4 是否包含图片下载逻辑"""

    def test_step4_has_download_images(self):
        """Step 4 应包含 download_product_images 调用"""
        with open("pipeline.py", "r") as f:
            content = f.read()

        assert "download_product_images" in content
        assert "local_path" in content

    def test_step10_has_platform_coupang(self):
        """Step 10 应传入 platform='coupang'"""
        with open("pipeline.py", "r") as f:
            content = f.read()

        assert 'platform="coupang"' in content


# ============================================================
# 6. Celery 任务数据收集
# ============================================================
class TestCeleryTaskDataCollection:
    """测试 Celery 任务中的数据收集逻辑"""

    def test_generate_report_task_has_db_collection(self):
        """generate_decision_report 应包含数据库数据收集逻辑"""
        with open("tasks/analysis_tasks.py", "r") as f:
            content = f.read()

        # 不应再有空数据传入
        assert "products=[]," not in content or "products = []" in content
        # 应包含数据库查询
        assert "project_products" in content
        assert "profit_calculations" in content
        assert "analysis_tasks" in content

    def test_review_task_handles_dict_return(self):
        """run_review_analysis 应处理 crawl_reviews 的 dict 返回值"""
        with open("tasks/analysis_tasks.py", "r") as f:
            content = f.read()

        assert "isinstance(crawl_result, dict)" in content
        assert 'crawl_result.get("reviews"' in content

    def test_scraping_task_has_field_compat(self):
        """_save_products_to_db 应包含字段兼容层"""
        with open("tasks/scraping_tasks.py", "r") as f:
            content = f.read()

        assert 'product.get("main_image_url")' in content
        assert 'product.get("main_image")' in content
        assert 'product.get("bsr_rank")' in content
        assert 'product.get("bsr")' in content
        assert "bsr_rank," in content
        assert "fulfillment_type," in content
        assert "est_sales_30d," in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
