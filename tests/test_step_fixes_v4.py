"""
Step 修复 V4 - 数据持久化字段完整性测试
测试:
1. project_routes INSERT 包含 est_sales_30d 和 bsr_category
2. scraping_tasks INSERT 包含 bsr_category
3. analysis_routes product endpoint SQL 使用正确字段名
4. export_routes SQL 使用正确字段名
"""
import ast
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProjectRoutesInsert:
    """测试 project_routes.py 的 INSERT 语句字段完整性"""

    def test_insert_includes_est_sales_30d(self):
        """INSERT 应包含 est_sales_30d 字段"""
        with open("api/project_routes.py", "r") as f:
            content = f.read()
        # 查找 INSERT INTO project_products 语句
        inserts = re.findall(
            r"INSERT INTO project_products\s*\(([^)]+)\)",
            content, re.DOTALL
        )
        assert len(inserts) > 0, "未找到 INSERT INTO project_products"
        for insert in inserts:
            assert "est_sales_30d" in insert, \
                f"INSERT 缺少 est_sales_30d 字段: {insert[:100]}"

    def test_insert_includes_bsr_category(self):
        """INSERT 应包含 bsr_category 字段"""
        with open("api/project_routes.py", "r") as f:
            content = f.read()
        inserts = re.findall(
            r"INSERT INTO project_products\s*\(([^)]+)\)",
            content, re.DOTALL
        )
        for insert in inserts:
            assert "bsr_category" in insert, \
                f"INSERT 缺少 bsr_category 字段: {insert[:100]}"

    def test_insert_values_count_matches_columns(self):
        """INSERT 的 VALUES 占位符数量应与列数匹配"""
        with open("api/project_routes.py", "r") as f:
            content = f.read()
        # 找到 INSERT...VALUES 对
        pattern = r"INSERT INTO project_products\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)"
        matches = re.findall(pattern, content, re.DOTALL)
        for cols, vals in matches:
            col_count = len([c.strip() for c in cols.split(",") if c.strip()])
            val_count = len([v.strip() for v in vals.split(",") if v.strip()])
            assert col_count == val_count, \
                f"列数 {col_count} != 占位符数 {val_count}"


class TestScrapingTasksInsert:
    """测试 scraping_tasks.py 的 INSERT 语句字段完整性"""

    def test_insert_includes_bsr_category(self):
        """INSERT 应包含 bsr_category 字段"""
        with open("tasks/scraping_tasks.py", "r") as f:
            content = f.read()
        inserts = re.findall(
            r"INSERT INTO project_products\s*\(([^)]+)\)",
            content, re.DOTALL
        )
        assert len(inserts) > 0, "未找到 INSERT INTO project_products"
        for insert in inserts:
            assert "bsr_category" in insert, \
                f"INSERT 缺少 bsr_category 字段: {insert[:100]}"

    def test_insert_values_count_matches_columns(self):
        """INSERT 的 VALUES 占位符数量应与列数匹配"""
        with open("tasks/scraping_tasks.py", "r") as f:
            content = f.read()
        pattern = r"INSERT INTO project_products\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)"
        matches = re.findall(pattern, content, re.DOTALL)
        for cols, vals in matches:
            col_count = len([c.strip() for c in cols.split(",") if c.strip()])
            val_count = len([v.strip() for v in vals.split(",") if v.strip()])
            assert col_count == val_count, \
                f"列数 {col_count} != 占位符数 {val_count}"


class TestAnalysisRoutesProductSQL:
    """测试 analysis_routes.py 的 product endpoint SQL 字段名"""

    def test_uses_main_image_url_not_image_url(self):
        """SELECT 应使用 main_image_url 而非 image_url"""
        with open("api/analysis_routes.py", "r") as f:
            content = f.read()
        # 在 product endpoint 的 SQL 中不应直接使用 pp.image_url
        assert "pp.image_url" not in content, \
            "SQL 中不应使用 pp.image_url（应为 pp.main_image_url）"

    def test_uses_bsr_rank_not_bsr_current(self):
        """SELECT 应使用 bsr_rank 而非 bsr_current"""
        with open("api/analysis_routes.py", "r") as f:
            content = f.read()
        assert "bsr_current" not in content, \
            "SQL 中不应使用 bsr_current（应为 bsr_rank）"

    def test_uses_bsr_category_not_category_name(self):
        """SELECT 应使用 bsr_category 而非 category_name"""
        with open("api/analysis_routes.py", "r") as f:
            content = f.read()
        assert "category_name" not in content, \
            "SQL 中不应使用 category_name（应为 bsr_category）"

    def test_uses_result_data_not_result(self):
        """SELECT 应使用 result_data 而非 result"""
        with open("api/analysis_routes.py", "r") as f:
            content = f.read()
        # 检查 SELECT 语句中不应有 "SELECT result FROM" 或 "SELECT result,"
        bad_patterns = re.findall(r"SELECT\s+result\s+FROM|SELECT\s+result,", content)
        assert len(bad_patterns) == 0, \
            f"SQL 中使用了 'result' 而非 'result_data': {bad_patterns}"


class TestExportRoutesSQL:
    """测试 export_routes.py 的 SQL 字段名"""

    def test_no_result_json_field(self):
        """不应使用 result_json 字段（应为 result_data）"""
        with open("api/export_routes.py", "r") as f:
            content = f.read()
        assert "result_json" not in content, \
            "SQL 中不应使用 result_json（应为 result_data）"

    def test_uses_correct_product_fields(self):
        """产品查询应使用正确的字段名"""
        with open("api/export_routes.py", "r") as f:
            content = f.read()
        # 不应在 SQL 中使用 monthly_sales, revenue, fba_fee 等不存在的字段
        # (这些是前端别名，不是数据库字段)
        bad_fields = []
        for field in ["pp.monthly_sales", "pp.revenue", "pp.fba_fee",
                       "pp.profit_margin", "pp.competition_level",
                       "pp.opportunity_score"]:
            if field in content:
                bad_fields.append(field)
        assert len(bad_fields) == 0, \
            f"SQL 中使用了不存在的字段: {bad_fields}"


class TestFieldMappingConsistency:
    """测试字段映射的一致性"""

    def test_product_data_has_frontend_aliases(self):
        """_db_get_products 应添加前端兼容别名"""
        with open("api/project_routes.py", "r") as f:
            content = f.read()
        # 检查兼容别名
        for alias in ["row[\"price\"]", "row[\"bsr\"]", "row[\"monthly_sales\"]",
                       "row[\"main_image\"]", "row[\"fulfillment\"]"]:
            assert alias in content, f"缺少前端兼容别名: {alias}"

    def test_all_data_paths_include_est_sales(self):
        """所有数据入库路径都应包含 est_sales_30d"""
        for filepath in ["api/project_routes.py", "tasks/scraping_tasks.py"]:
            with open(filepath, "r") as f:
                content = f.read()
            inserts = re.findall(
                r"INSERT INTO project_products\s*\(([^)]+)\)",
                content, re.DOTALL
            )
            for insert in inserts:
                assert "est_sales_30d" in insert, \
                    f"{filepath}: INSERT 缺少 est_sales_30d"
