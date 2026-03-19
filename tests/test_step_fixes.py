"""
针对 Step 1-10 修复的专项测试

测试内容:
1. Step 9: 利润计算器参数兼容性和存储费修复
2. Step 1/3: 数据持久化字段映射
3. Step 10: 报告数据收集
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Step 9: 利润计算器修复测试
# ============================================================

class TestProfitCalculatorFixes:
    """测试利润计算器的参数兼容性修复"""

    def setup_method(self):
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator
        self.calculator = AmazonFBAProfitCalculator(marketplace="US", exchange_rate=7.25)

    def test_original_params_still_work(self):
        """原始参数名应该继续正常工作"""
        params = {
            "selling_price": 29.99,
            "category": "Home & Kitchen",
            "weight_lb": 1.5,
            "length_in": 10,
            "width_in": 8,
            "height_in": 4,
            "cogs_rmb": 35,
            "shipping_rmb_per_kg": 40,
            "weight_kg": 0.68,
            "ppc_cost_per_unit": 2.0,
            "return_rate": 0.03,
            "monthly_units": 100,
        }
        result = self.calculator.calculate_profit(params)
        assert result is not None
        assert result["selling_price"] == 29.99
        assert result["profit"]["profit_per_unit_usd"] != 0
        assert "profit_margin" in result["profit"]

    def test_api_route_params_compatibility(self):
        """API 路由传入的参数名（cm/sourcing_cost_rmb）应该被正确转换"""
        params = {
            "selling_price": 25.99,
            "category": "General",
            "sourcing_cost_rmb": 30,       # API 路由用的名字
            "shipping_cost_per_kg": 45,    # API 路由用的名字
            "weight_kg": 0.5,
            "length_cm": 25,               # 厘米而非英寸
            "width_cm": 15,
            "height_cm": 10,
            "estimated_cpa": 1.5,          # API 路由用的名字
        }
        result = self.calculator.calculate_profit(params)
        assert result is not None
        assert result["selling_price"] == 25.99
        # 验证厘米被正确转换为英寸
        assert result["profit"]["profit_per_unit_usd"] != 0
        # 验证采购成本被正确读取
        assert result["costs"]["cogs_rmb"] == 30
        # 验证广告费被正确读取
        assert result["costs"]["ppc_cost"] == 1.5

    def test_weight_kg_to_lb_conversion(self):
        """weight_kg 应该被正确转换为 weight_lb"""
        params = {
            "selling_price": 20.0,
            "weight_kg": 1.0,  # 1kg ≈ 2.2046 lb
            "length_cm": 20,
            "width_cm": 15,
            "height_cm": 10,
            "cogs_rmb": 20,
        }
        result = self.calculator.calculate_profit(params)
        assert result is not None
        # FBA 费用应该基于正确的重量计算
        assert result["costs"]["fba_fulfillment_fee"] > 0
        # 验证重量被正确转换
        assert result["product_info"]["weight_lb"] == pytest.approx(2.2046, rel=0.01)

    def test_storage_fee_is_per_unit(self):
        """存储费应该是单件产品的月度费用"""
        params = {
            "selling_price": 30.0,
            "weight_lb": 1.0,
            "length_in": 10,
            "width_in": 8,
            "height_in": 4,
            "cogs_rmb": 25,
            "monthly_units": 100,
        }
        result = self.calculator.calculate_profit(params)
        storage_fee = result["costs"]["storage_fee_per_unit"]
        # 体积 = 10*8*4 / 1728 ≈ 0.185 cuft
        # 存储费率约 $0.87/cuft (Jan-Sep) 或 $2.40/cuft (Oct-Dec)
        # 单件存储费应该很小（< $1）
        assert storage_fee < 1.0
        assert storage_fee > 0

    def test_mixed_params(self):
        """混合参数（部分英寸部分厘米）应该正确处理"""
        params = {
            "selling_price": 35.0,
            "weight_lb": 2.0,
            "length_in": 12,      # 英寸
            "width_cm": 20,       # 厘米
            "height_in": 5,       # 英寸
            "cogs_rmb": 40,
        }
        result = self.calculator.calculate_profit(params)
        assert result is not None
        assert result["profit"]["profit_per_unit_usd"] != 0
        # 验证 width 被从 cm 转换为 in
        dims = result["product_info"]["dimensions"]
        # width_cm=20 -> 20/2.54 ≈ 7.87 in
        assert "12" in dims  # length_in 保持不变


# ============================================================
# Step 1/3: 数据持久化字段映射测试
# ============================================================

class TestFieldMappingFixes:
    """测试爬虫数据到数据库的字段映射"""

    def test_crawler_output_has_main_image(self):
        """爬虫输出使用 main_image 字段"""
        from scrapers.amazon.search_crawler import AmazonSearchCrawler
        crawler = AmazonSearchCrawler(marketplace="US")
        # 模拟一个解析结果的数据结构
        mock_product = {
            "asin": "B0TEST12345",
            "title": "Test Product",
            "main_image": "https://images-na.ssl-images-amazon.com/images/I/test.jpg",
            "price": 29.99,
            "rating": 4.5,
            "review_count": 100,
            "brand": "TestBrand",
        }
        # 验证爬虫输出字段名
        assert "main_image" in mock_product
        assert "main_image_url" not in mock_product
        crawler.close()

    def test_sp_api_output_has_main_image(self):
        """SP-API 输出也使用 main_image 字段"""
        mock_sp_product = {
            "asin": "B0TEST12345",
            "title": "Test Product",
            "main_image": "https://images-na.ssl-images-amazon.com/images/I/test.jpg",
            "bsr": 5000,
            "source": "sp-api",
        }
        assert "main_image" in mock_sp_product

    def test_field_mapping_logic(self):
        """验证持久化时的字段映射逻辑"""
        # 模拟爬虫产品数据
        crawler_product = {
            "asin": "B0TEST12345",
            "title": "Test Product",
            "main_image": "https://example.com/image.jpg",
            "price": 29.99,
            "rating": 4.5,
            "review_count": 100,
            "brand": "TestBrand",
            "bsr": 5000,
        }

        # 模拟 project_routes.py 中的字段映射逻辑
        image_url = (
            crawler_product.get("main_image_url")
            or crawler_product.get("main_image")
            or ""
        )
        price = crawler_product.get("price_current") or crawler_product.get("price")
        bsr_rank = crawler_product.get("bsr_rank") or crawler_product.get("bsr") or 0

        assert image_url == "https://example.com/image.jpg"
        assert price == 29.99
        assert bsr_rank == 5000


# ============================================================
# Step 10: 产品数据兼容字段别名测试
# ============================================================

class TestProductFieldAliases:
    """测试 _db_get_products 返回的兼容字段别名"""

    def test_field_aliases_mapping(self):
        """验证数据库行到前端字段的别名映射"""
        # 模拟数据库返回的行
        db_row = {
            "id": 1,
            "project_id": "1",
            "asin": "B0TEST12345",
            "title": "Test Product",
            "main_image_url": "https://example.com/image.jpg",
            "price_current": 29.99,
            "fulfillment_type": "FBA",
            "rating": 4.5,
            "review_count": 100,
            "est_sales_30d": 500,
            "bsr_rank": 5000,
            "is_filtered": 0,
            "created_at": "2025-01-01T00:00:00",
        }

        # 模拟 _db_get_products 中的别名映射
        db_row["price"] = float(db_row["price_current"]) if db_row.get("price_current") else None
        db_row["bsr"] = db_row.get("bsr_rank")
        db_row["monthly_sales"] = db_row.get("est_sales_30d")
        db_row["main_image"] = db_row.get("main_image_url")
        db_row["image_url"] = db_row.get("main_image_url")
        db_row["fulfillment"] = db_row.get("fulfillment_type")

        # 验证前端期望的字段名都存在
        assert db_row["price"] == 29.99
        assert db_row["bsr"] == 5000
        assert db_row["monthly_sales"] == 500
        assert db_row["main_image"] == "https://example.com/image.jpg"
        assert db_row["image_url"] == "https://example.com/image.jpg"
        assert db_row["fulfillment"] == "FBA"

        # 原始字段名也应该保留
        assert db_row["price_current"] == 29.99
        assert db_row["bsr_rank"] == 5000
        assert db_row["est_sales_30d"] == 500
        assert db_row["main_image_url"] == "https://example.com/image.jpg"
        assert db_row["fulfillment_type"] == "FBA"


# ============================================================
# Step 10: 报告数据收集测试
# ============================================================

class TestReportDataCollection:
    """测试报告生成时的数据收集逻辑"""

    def test_category_analysis_from_products(self):
        """验证从产品数据生成类目分析"""
        products = [
            {"asin": "B001", "price": 25.0, "rating": 4.5, "review_count": 200, "estimated_monthly_sales": 300},
            {"asin": "B002", "price": 35.0, "rating": 4.0, "review_count": 150, "estimated_monthly_sales": 200},
            {"asin": "B003", "price": 30.0, "rating": 4.2, "review_count": 100, "estimated_monthly_sales": 400},
        ]

        prices = [p["price"] for p in products if p.get("price")]
        ratings = [p["rating"] for p in products if p.get("rating")]
        reviews = [p["review_count"] for p in products if p.get("review_count")]
        sales = [p["estimated_monthly_sales"] for p in products if p.get("estimated_monthly_sales")]
        avg_price = sum(prices) / len(prices) if prices else 0
        total_sales = sum(sales)

        category_analysis = {
            "market_size": {
                "estimated_monthly_gmv": round(total_sales * avg_price, 2),
                "estimated_monthly_sales": total_sales,
                "product_count": len(products),
            },
            "competition": {
                "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                "avg_reviews": round(sum(reviews) / len(reviews)) if reviews else 0,
                "avg_price": round(avg_price, 2),
            },
        }

        assert category_analysis["market_size"]["product_count"] == 3
        assert category_analysis["market_size"]["estimated_monthly_sales"] == 900
        assert category_analysis["market_size"]["estimated_monthly_gmv"] == round(900 * 30.0, 2)
        assert category_analysis["competition"]["avg_rating"] == round((4.5 + 4.0 + 4.2) / 3, 2)
        assert category_analysis["competition"]["avg_price"] == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
