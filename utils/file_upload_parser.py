"""
文件上传解析模块
对应 PRD 3.1.1 - 输入方式 2：上传后台数据表

支持:
- .csv 和 .xlsx 格式（亚马逊后台 Search Term Report）
- 自动读取表头并进行字段映射
- 双重匹配降级逻辑（ASIN 优先 → Search Term 降级）
"""

import os
import io
import csv
import json
from typing import Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger()


class FileUploadParser:
    """
    后台数据表上传解析器

    解析用户上传的 Amazon Search Term Report 或自定义数据表，
    自动识别 ASIN 列和 Search Term 列，输出标准化的产品列表。
    """

    # 常见的 ASIN 列名映射
    ASIN_COLUMN_ALIASES = [
        "asin", "ASIN", "Asin",
        "customer_search_term_asin", "Customer Search Term ASIN",
        "advertised_asin", "Advertised ASIN",
        "product_asin", "Product ASIN",
        "asin_value", "ASIN Value",
    ]

    # 常见的 Search Term 列名映射
    SEARCH_TERM_ALIASES = [
        "search_term", "Search Term", "search term",
        "customer_search_term", "Customer Search Term",
        "keyword", "Keyword", "Keywords",
        "query", "Query", "search_query",
    ]

    # 常见的其他有用列名映射
    IMPRESSIONS_ALIASES = ["impressions", "Impressions", "impression"]
    CLICKS_ALIASES = ["clicks", "Clicks", "click", "Click"]
    SALES_ALIASES = [
        "7_day_total_sales", "7 Day Total Sales",
        "sales", "Sales", "total_sales", "Total Sales",
        "orders", "Orders", "7_day_total_orders",
    ]
    SPEND_ALIASES = ["spend", "Spend", "cost", "Cost"]
    CTR_ALIASES = ["ctr", "CTR", "click_through_rate", "Click-Through Rate"]
    CVR_ALIASES = [
        "conversion_rate", "Conversion Rate",
        "7_day_conversion_rate", "7 Day Conversion Rate",
    ]

    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
    MAX_FILE_SIZE_MB = 50

    def __init__(self):
        self.detected_columns = {}
        self.raw_headers = []

    def parse_file(self, file_path: str) -> dict:
        """
        解析上传的文件

        :param file_path: 文件路径
        :return: {
            "success": bool,
            "headers": list,           # 原始表头
            "column_mapping": dict,    # 自动检测的列映射
            "rows": list[dict],        # 解析后的数据行
            "total_rows": int,
            "asin_count": int,         # 包含 ASIN 的行数
            "search_term_count": int,  # 包含 Search Term 的行数
            "error": str | None,
        }
        """
        # 校验文件
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": f"不支持的文件格式: {ext}，仅支持 .csv 和 .xlsx",
            }

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            return {
                "success": False,
                "error": f"文件大小 ({file_size_mb:.1f}MB) 超过限制 ({self.MAX_FILE_SIZE_MB}MB)",
            }

        try:
            if ext == ".csv":
                rows, headers = self._parse_csv(file_path)
            else:
                rows, headers = self._parse_excel(file_path)

            self.raw_headers = headers

            # 自动检测列映射
            column_mapping = self._auto_detect_columns(headers)
            self.detected_columns = column_mapping

            # 标准化数据
            standardized_rows = self._standardize_rows(rows, column_mapping)

            # 统计
            asin_count = sum(1 for r in standardized_rows if r.get("asin"))
            search_term_count = sum(
                1 for r in standardized_rows if r.get("search_term")
            )

            logger.info(
                f"文件解析完成: {len(standardized_rows)} 行, "
                f"{asin_count} 个 ASIN, {search_term_count} 个 Search Term"
            )

            return {
                "success": True,
                "headers": headers,
                "column_mapping": column_mapping,
                "rows": standardized_rows,
                "total_rows": len(standardized_rows),
                "asin_count": asin_count,
                "search_term_count": search_term_count,
                "error": None,
            }

        except Exception as e:
            logger.error(f"文件解析失败: {e}")
            return {
                "success": False,
                "error": f"文件解析失败: {str(e)}",
            }

    def _parse_csv(self, file_path: str) -> tuple:
        """解析 CSV 文件"""
        rows = []
        headers = []

        # 尝试检测编码
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    # 检测分隔符
                    sample = f.read(4096)
                    f.seek(0)

                    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                    reader = csv.DictReader(f, dialect=dialect)

                    headers = reader.fieldnames or []
                    for row in reader:
                        rows.append(dict(row))

                    return rows, headers
            except (UnicodeDecodeError, csv.Error):
                continue

        raise ValueError("无法解析 CSV 文件，请检查文件编码")

    def _parse_excel(self, file_path: str) -> tuple:
        """解析 Excel 文件"""
        try:
            import openpyxl
        except ImportError:
            raise ImportError("需要安装 openpyxl: pip install openpyxl")

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active

        rows = []
        headers = []

        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(cell) if cell else f"Column_{j}" for j, cell in enumerate(row)]
            else:
                row_dict = {}
                for j, cell in enumerate(row):
                    if j < len(headers):
                        row_dict[headers[j]] = str(cell) if cell is not None else ""
                if any(v.strip() for v in row_dict.values()):
                    rows.append(row_dict)

        wb.close()
        return rows, headers

    def _auto_detect_columns(self, headers: list) -> dict:
        """
        自动检测列映射

        :return: {
            "asin": "原始列名" | None,
            "search_term": "原始列名" | None,
            "impressions": "原始列名" | None,
            "clicks": "原始列名" | None,
            "sales": "原始列名" | None,
            "spend": "原始列名" | None,
            "ctr": "原始列名" | None,
            "cvr": "原始列名" | None,
        }
        """
        mapping = {}

        def find_match(aliases):
            for alias in aliases:
                for header in headers:
                    if header.strip().lower() == alias.lower():
                        return header
                    if alias.lower() in header.strip().lower():
                        return header
            return None

        mapping["asin"] = find_match(self.ASIN_COLUMN_ALIASES)
        mapping["search_term"] = find_match(self.SEARCH_TERM_ALIASES)
        mapping["impressions"] = find_match(self.IMPRESSIONS_ALIASES)
        mapping["clicks"] = find_match(self.CLICKS_ALIASES)
        mapping["sales"] = find_match(self.SALES_ALIASES)
        mapping["spend"] = find_match(self.SPEND_ALIASES)
        mapping["ctr"] = find_match(self.CTR_ALIASES)
        mapping["cvr"] = find_match(self.CVR_ALIASES)

        logger.info(f"自动列映射: {json.dumps(mapping, ensure_ascii=False)}")
        return mapping

    def update_column_mapping(self, mapping: dict):
        """
        用户手动更新列映射（前端确认后调用）

        :param mapping: {"asin": "用户选择的列名", "search_term": "..."}
        """
        self.detected_columns.update(mapping)

    def _standardize_rows(self, rows: list, column_mapping: dict) -> list:
        """将原始行数据标准化为统一格式"""
        standardized = []

        for row in rows:
            item = {"_raw": row}  # 保留原始数据

            # 提取 ASIN
            asin_col = column_mapping.get("asin")
            if asin_col and asin_col in row:
                asin = str(row[asin_col]).strip().upper()
                if len(asin) == 10 and asin.startswith("B"):
                    item["asin"] = asin
                else:
                    item["asin"] = None
            else:
                item["asin"] = None

            # 提取 Search Term
            st_col = column_mapping.get("search_term")
            if st_col and st_col in row:
                item["search_term"] = str(row[st_col]).strip()
            else:
                item["search_term"] = None

            # 提取数值字段
            for field in ["impressions", "clicks", "sales", "spend"]:
                col = column_mapping.get(field)
                if col and col in row:
                    try:
                        val = str(row[col]).replace(",", "").replace("$", "").strip()
                        item[field] = float(val) if val else 0
                    except (ValueError, TypeError):
                        item[field] = 0
                else:
                    item[field] = 0

            # 提取百分比字段
            for field in ["ctr", "cvr"]:
                col = column_mapping.get(field)
                if col and col in row:
                    try:
                        val = str(row[col]).replace("%", "").strip()
                        item[field] = float(val) if val else 0
                    except (ValueError, TypeError):
                        item[field] = 0
                else:
                    item[field] = 0

            standardized.append(item)

        return standardized

    def get_asins_for_lookup(self, rows: list) -> list:
        """
        从解析结果中提取 ASIN 列表，用于后续 SP-API 查询

        实现 PRD 3.1.2 的双重匹配降级逻辑：
        - 有 ASIN 的行直接返回 ASIN
        - 无 ASIN 但有 Search Term 的行标记为需要关键词搜索
        """
        lookup_items = []

        for row in rows:
            if row.get("asin"):
                lookup_items.append({
                    "type": "asin",
                    "value": row["asin"],
                    "search_term": row.get("search_term", ""),
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                })
            elif row.get("search_term"):
                lookup_items.append({
                    "type": "search_term",
                    "value": row["search_term"],
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                })

        logger.info(
            f"提取查询项: {len(lookup_items)} 个 "
            f"(ASIN: {sum(1 for i in lookup_items if i['type'] == 'asin')}, "
            f"Search Term: {sum(1 for i in lookup_items if i['type'] == 'search_term')})"
        )

        return lookup_items


class FileUploadAPI:
    """
    文件上传 API 路由辅助类
    处理文件保存和临时存储
    """

    UPLOAD_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "uploads",
    )

    @classmethod
    def save_upload(cls, file_storage, user_id: int) -> dict:
        """
        保存上传的文件

        :param file_storage: Flask request.files 中的文件对象
        :param user_id: 用户 ID
        :return: {"file_id": str, "file_path": str, "filename": str}
        """
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)

        filename = file_storage.filename
        ext = os.path.splitext(filename)[1].lower()

        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = f"upload_{user_id}_{timestamp}"
        safe_filename = f"{file_id}{ext}"
        file_path = os.path.join(cls.UPLOAD_DIR, safe_filename)

        file_storage.save(file_path)

        logger.info(f"文件已保存: {file_path} (用户: {user_id})")

        return {
            "file_id": file_id,
            "file_path": file_path,
            "filename": filename,
        }

    @classmethod
    def parse_upload(cls, file_path: str) -> dict:
        """解析已保存的上传文件"""
        parser = FileUploadParser()
        return parser.parse_file(file_path)
