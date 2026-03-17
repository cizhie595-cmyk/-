"""
Amazon 后台数据解析器

解析用户从亚马逊后台下载的报告文件：
  - Search Term Report（搜索词报告）
  - Business Report（业务报告）
  - Inventory Report（库存报告）

根据 ASIN 或标题进行精准匹配，补充流量和转化数据。
"""

import csv
import io
import os
import re
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class AmazonBackendParser:
    """
    Amazon 后台报告解析器

    支持解析用户上传的 CSV/TSV 格式报告，
    提取搜索词、点击量、转化率等后台流量数据。
    """

    # 搜索词报告的标准列名映射
    SEARCH_TERM_COLUMNS = {
        "Search Term": "search_term",
        "Search Frequency Rank": "search_frequency_rank",
        "#1 Clicked ASIN": "clicked_asin_1",
        "#1 Product Title": "clicked_title_1",
        "#1 Click Share": "click_share_1",
        "#1 Conversion Share": "conversion_share_1",
        "#2 Clicked ASIN": "clicked_asin_2",
        "#2 Product Title": "clicked_title_2",
        "#2 Click Share": "click_share_2",
        "#2 Conversion Share": "conversion_share_2",
        "#3 Clicked ASIN": "clicked_asin_3",
        "#3 Product Title": "clicked_title_3",
        "#3 Click Share": "click_share_3",
        "#3 Conversion Share": "conversion_share_3",
    }

    # 业务报告的标准列名映射
    BUSINESS_REPORT_COLUMNS = {
        "(Parent) ASIN": "parent_asin",
        "(Child) ASIN": "child_asin",
        "Title": "title",
        "Sessions": "sessions",
        "Session Percentage": "session_pct",
        "Page Views": "page_views",
        "Page Views Percentage": "page_views_pct",
        "Buy Box Percentage": "buy_box_pct",
        "Units Ordered": "units_ordered",
        "Unit Session Percentage": "conversion_rate",
        "Ordered Product Sales": "ordered_sales",
        "Total Order Items": "total_order_items",
    }

    def __init__(self):
        self._search_term_data = []
        self._business_report_data = []

    # ================================================================
    # 搜索词报告解析
    # ================================================================

    def parse_search_term_report(self, file_path: str) -> list[dict]:
        """
        解析亚马逊搜索词报告（Brand Analytics）。

        :param file_path: CSV/TSV 文件路径
        :return: 解析后的搜索词数据列表
        """
        logger.info(f"[后台解析] 开始解析搜索词报告: {file_path}")

        data = self._read_report_file(file_path)
        if not data:
            return []

        parsed = []
        for row in data:
            record = {}
            for original_col, mapped_col in self.SEARCH_TERM_COLUMNS.items():
                value = row.get(original_col, "")
                # 清理百分比格式
                if "share" in mapped_col or "pct" in mapped_col:
                    value = self._parse_percentage(value)
                elif "rank" in mapped_col:
                    value = self._parse_int(value)
                record[mapped_col] = value
            parsed.append(record)

        self._search_term_data = parsed
        logger.info(f"[后台解析] 搜索词报告解析完成: {len(parsed)} 条记录")
        return parsed

    def parse_business_report(self, file_path: str) -> list[dict]:
        """
        解析亚马逊业务报告（Detail Page Sales and Traffic）。

        :param file_path: CSV/TSV 文件路径
        :return: 解析后的业务数据列表
        """
        logger.info(f"[后台解析] 开始解析业务报告: {file_path}")

        data = self._read_report_file(file_path)
        if not data:
            return []

        parsed = []
        for row in data:
            record = {}
            for original_col, mapped_col in self.BUSINESS_REPORT_COLUMNS.items():
                value = row.get(original_col, "")
                if mapped_col in ("sessions", "page_views", "units_ordered", "total_order_items"):
                    value = self._parse_int(value)
                elif "pct" in mapped_col or "rate" in mapped_col:
                    value = self._parse_percentage(value)
                elif "sales" in mapped_col:
                    value = self._parse_currency(value)
                record[mapped_col] = value
            parsed.append(record)

        self._business_report_data = parsed
        logger.info(f"[后台解析] 业务报告解析完成: {len(parsed)} 条记录")
        return parsed

    # ================================================================
    # 数据匹配
    # ================================================================

    def match_products(self, products: list[dict],
                       match_field: str = "asin") -> list[dict]:
        """
        将后台数据与爬取的产品列表进行匹配。

        :param products: 爬取的产品列表
        :param match_field: 匹配字段 (asin / title)
        :return: 补充了后台数据的产品列表
        """
        logger.info(f"[后台解析] 开始匹配 {len(products)} 个产品 | 匹配字段: {match_field}")

        matched_count = 0

        for product in products:
            product_key = product.get(match_field, "")
            if not product_key:
                continue

            # 匹配搜索词报告
            search_matches = self._find_in_search_terms(product_key, match_field)
            if search_matches:
                product["search_term_data"] = search_matches
                product["top_search_terms"] = [m["search_term"] for m in search_matches[:5]]

            # 匹配业务报告
            biz_match = self._find_in_business_report(product_key, match_field)
            if biz_match:
                product["backend_data"] = biz_match
                product["sessions"] = biz_match.get("sessions", 0)
                product["page_views"] = biz_match.get("page_views", 0)
                product["conversion_rate"] = biz_match.get("conversion_rate", 0)
                product["units_ordered"] = biz_match.get("units_ordered", 0)
                product["buy_box_pct"] = biz_match.get("buy_box_pct", 0)
                matched_count += 1

        logger.info(f"[后台解析] 匹配完成: {matched_count}/{len(products)} 个产品命中后台数据")
        return products

    def _find_in_search_terms(self, key: str, field: str) -> list[dict]:
        """在搜索词报告中查找匹配记录"""
        matches = []
        for record in self._search_term_data:
            # 检查3个位置的ASIN/标题
            for i in range(1, 4):
                asin_field = f"clicked_asin_{i}"
                title_field = f"clicked_title_{i}"

                if field == "asin" and record.get(asin_field) == key:
                    matches.append({
                        "search_term": record.get("search_term", ""),
                        "search_frequency_rank": record.get("search_frequency_rank", 0),
                        "position": i,
                        "click_share": record.get(f"click_share_{i}", 0),
                        "conversion_share": record.get(f"conversion_share_{i}", 0),
                    })
                elif field == "title":
                    record_title = record.get(title_field, "").lower()
                    if key.lower() in record_title or record_title in key.lower():
                        matches.append({
                            "search_term": record.get("search_term", ""),
                            "search_frequency_rank": record.get("search_frequency_rank", 0),
                            "position": i,
                            "click_share": record.get(f"click_share_{i}", 0),
                            "conversion_share": record.get(f"conversion_share_{i}", 0),
                        })

        # 按搜索频率排名排序
        matches.sort(key=lambda x: x.get("search_frequency_rank", 999999))
        return matches

    def _find_in_business_report(self, key: str, field: str) -> Optional[dict]:
        """在业务报告中查找匹配记录"""
        for record in self._business_report_data:
            if field == "asin":
                if record.get("child_asin") == key or record.get("parent_asin") == key:
                    return record
            elif field == "title":
                record_title = record.get("title", "").lower()
                if key.lower() in record_title:
                    return record
        return None

    # ================================================================
    # 工具方法
    # ================================================================

    def _read_report_file(self, file_path: str) -> list[dict]:
        """读取 CSV/TSV 报告文件"""
        if not os.path.exists(file_path):
            logger.error(f"[后台解析] 文件不存在: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()

            # 自动检测分隔符
            delimiter = "\t" if "\t" in content.split("\n")[0] else ","

            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            return list(reader)

        except Exception as e:
            logger.error(f"[后台解析] 文件读取失败: {e}")
            return []

    @staticmethod
    def _parse_percentage(value) -> float:
        """解析百分比字符串"""
        if isinstance(value, (int, float)):
            return float(value)
        if not value or not isinstance(value, str):
            return 0.0
        cleaned = value.strip().replace("%", "").replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_int(value) -> int:
        """解析整数字符串"""
        if isinstance(value, int):
            return value
        if not value or not isinstance(value, str):
            return 0
        cleaned = value.strip().replace(",", "").replace(".", "")
        try:
            return int(cleaned)
        except ValueError:
            return 0

    @staticmethod
    def _parse_currency(value) -> float:
        """解析货币字符串"""
        if isinstance(value, (int, float)):
            return float(value)
        if not value or not isinstance(value, str):
            return 0.0
        cleaned = re.sub(r"[^\d.]", "", value)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
