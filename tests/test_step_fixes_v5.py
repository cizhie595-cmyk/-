"""
测试 V5: 利润计算保存/查询字段完整性 + 前端 payload 字段对齐
"""
import pytest
import json


class TestProfitRoutesSaveFields:
    """测试 profit_routes.py 的 INSERT 和 SELECT 字段完整性"""

    def test_save_insert_includes_all_fields(self):
        """验证 INSERT 语句包含所有 profit_calculations 表字段"""
        with open("api/profit_routes.py", "r") as f:
            content = f.read()

        # INSERT 语句应包含这些字段
        required_fields = [
            "user_id", "asin", "selling_price", "sourcing_cost",
            "shipping_cost_per_kg", "estimated_cpa", "return_rate",
            "landed_cost", "amazon_fees",
            "net_profit", "net_margin", "roi",
        ]

        # 找到 INSERT INTO profit_calculations 的部分
        insert_start = content.find("INSERT INTO profit_calculations")
        assert insert_start > 0, "INSERT INTO profit_calculations not found"

        # 提取 INSERT 语句（到 VALUES 结束）
        insert_end = content.find(")", content.find("VALUES", insert_start)) + 1
        insert_sql = content[insert_start:insert_end]

        for field in required_fields:
            assert field in insert_sql, f"INSERT 缺少字段: {field}"

    def test_history_select_includes_all_fields(self):
        """验证 history SELECT 语句包含新增字段"""
        with open("api/profit_routes.py", "r") as f:
            content = f.read()

        # 找到 get_profit_history 函数中的 SELECT
        history_start = content.find("def get_profit_history")
        assert history_start > 0

        select_start = content.find("SELECT", history_start)
        select_end = content.find("FROM profit_calculations", select_start)
        select_sql = content[select_start:select_end]

        new_fields = [
            "shipping_cost_per_kg", "estimated_cpa", "return_rate",
            "landed_cost", "amazon_fees",
        ]
        for field in new_fields:
            assert field in select_sql, f"history SELECT 缺少字段: {field}"

    def test_save_record_builds_all_fields(self):
        """验证 record 字典包含所有需要的字段"""
        with open("api/profit_routes.py", "r") as f:
            content = f.read()

        # 找到 save_profit_calculation 函数中的 record 定义
        save_start = content.find("def save_profit_calculation")
        record_start = content.find("record = {", save_start)
        record_end = content.find("}", record_start) + 1
        record_text = content[record_start:record_end]

        required_keys = [
            "shipping_cost_per_kg", "estimated_cpa", "return_rate",
            "landed_cost", "amazon_fees",
        ]
        for key in required_keys:
            assert f'"{key}"' in record_text, f"record 字典缺少 key: {key}"


class TestFrontendProfitPayload:
    """测试前端利润计算器 save payload 字段完整性"""

    def test_save_payload_includes_cost_fields(self):
        """验证前端 saveCalculation 的 payload 包含成本字段"""
        with open("frontend/templates/profit_calculator.html", "r") as f:
            content = f.read()

        # 找到 saveCalculation 函数
        save_start = content.find("async function saveCalculation()")
        assert save_start > 0, "saveCalculation function not found"

        # 提取到函数结束
        save_end = content.find("async function", save_start + 10)
        if save_end < 0:
            save_end = len(content)
        save_func = content[save_start:save_end]

        # 验证 payload 包含新字段
        assert "shipping_cost_per_kg" in save_func, "payload 缺少 shipping_cost_per_kg"
        assert "estimated_cpa" in save_func, "payload 缺少 estimated_cpa"
        assert "return_rate" in save_func, "payload 缺少 return_rate"
        assert "landed_cost" in save_func, "payload 缺少 landed_cost"
        assert "amazon_fees" in save_func, "payload 缺少 amazon_fees"

    def test_save_extracts_api_result_costs(self):
        """验证 save 函数从 apiResult.costs 中提取费用数据"""
        with open("frontend/templates/profit_calculator.html", "r") as f:
            content = f.read()

        save_start = content.find("async function saveCalculation()")
        save_end = content.find("async function", save_start + 10)
        save_func = content[save_start:save_end]

        # 应该从 lastCalcResult.apiResult 提取 costs
        assert "apiResult" in save_func, "save 函数应引用 apiResult"
        assert "costs" in save_func, "save 函数应引用 costs"


class TestProfitCalculatorParamCompat:
    """测试利润计算器参数兼容性"""

    def test_calculate_profit_accepts_cm_params(self):
        """验证 calculate_profit 接受 cm 单位参数并自动转换"""
        import sys
        sys.path.insert(0, ".")
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator

        calc = AmazonFBAProfitCalculator(marketplace="US", exchange_rate=7.25)

        # 使用 cm 参数（前端传入的格式）
        params = {
            "selling_price": 29.99,
            "sourcing_cost_rmb": 35,
            "weight_kg": 0.5,
            "length_cm": 25,
            "width_cm": 15,
            "height_cm": 10,
            "category": "general",
            "shipping_cost_per_kg": 40,
            "estimated_cpa": 2.0,
            "return_rate": 0.05,
        }

        result = calc.calculate_profit(params)
        assert "profit" in result
        assert "costs" in result
        assert result["profit"]["profit_per_unit_usd"] != 0

    def test_batch_calculate_returns_list(self):
        """验证 batch_calculate 返回列表"""
        import sys
        sys.path.insert(0, ".")
        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator

        calc = AmazonFBAProfitCalculator(marketplace="US")

        products = [
            {"selling_price": 29.99, "sourcing_cost_rmb": 35, "asin": "B001"},
            {"selling_price": 19.99, "sourcing_cost_rmb": 20, "asin": "B002"},
        ]

        results = calc.batch_calculate(products)
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0].get("asin") == "B001"
        assert results[1].get("asin") == "B002"
