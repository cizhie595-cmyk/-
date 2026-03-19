"""
分析结果模型层
包含: CategoryModel, MonthlySummaryModel, ProductImageModel, ReviewAnalysisModel,
      DetailPageAnalysisModel, ProfitAnalysisModel, TrendDataModel, AnalysisReportModel,
      ProfitCalculationModel, Asset3DModel
对应表: categories, monthly_summary, product_images, review_analysis,
        detail_page_analysis, profit_analysis, trend_data, analysis_reports,
        profit_calculations, assets_3d
"""

import json
import uuid
from datetime import date, datetime
from typing import Optional
from database.connection import db


class CategoryModel:
    """商品分类模型 - 对应 categories 表"""

    @staticmethod
    def create(platform: str, category_id: str, category_name: str, **kwargs) -> int:
        data = {"platform": platform, "category_id": category_id,
                "category_name": category_name}
        data.update(kwargs)
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO categories ({fields}) VALUES ({placeholders})"
        return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def get_by_platform(platform: str, parent_id: int = None) -> list[dict]:
        sql = "SELECT * FROM categories WHERE platform = %s"
        params = [platform]
        if parent_id is not None:
            sql += " AND parent_id = %s"
            params.append(parent_id)
        else:
            sql += " AND parent_id IS NULL"
        sql += " ORDER BY category_name ASC"
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_by_id(cat_id: int) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM categories WHERE id = %s", (cat_id,))

    @staticmethod
    def upsert(platform: str, category_id: str, data: dict) -> int:
        existing = db.fetch_one(
            "SELECT id FROM categories WHERE platform = %s AND category_id = %s",
            (platform, category_id))
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE categories SET {set_clause} WHERE id = %s"
            db.execute(sql, (*data.values(), existing["id"]))
            return existing["id"]
        else:
            data["platform"] = platform
            data["category_id"] = category_id
            return CategoryModel.create(**data)

    @staticmethod
    def get_children(parent_id: int) -> list[dict]:
        return db.fetch_all(
            "SELECT * FROM categories WHERE parent_id = %s ORDER BY category_name", (parent_id,))


class MonthlySummaryModel:
    """月度汇总模型 - 对应 monthly_summary 表"""

    @staticmethod
    def upsert(product_id: int, summary_month: str, data: dict):
        existing = db.fetch_one(
            "SELECT id FROM monthly_summary WHERE product_id = %s AND summary_month = %s",
            (product_id, summary_month))
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE monthly_summary SET {set_clause} WHERE id = %s"
            db.execute(sql, (*data.values(), existing["id"]))
        else:
            data["product_id"] = product_id
            data["summary_month"] = summary_month
            fields = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO monthly_summary ({fields}) VALUES ({placeholders})"
            db.execute(sql, tuple(data.values()))

    @staticmethod
    def get_by_product(product_id: int, months: int = 12) -> list[dict]:
        sql = """SELECT * FROM monthly_summary WHERE product_id = %s
                 ORDER BY summary_month DESC LIMIT %s"""
        return db.fetch_all(sql, (product_id, months))

    @staticmethod
    def get_latest(product_id: int) -> Optional[dict]:
        sql = "SELECT * FROM monthly_summary WHERE product_id = %s ORDER BY summary_month DESC LIMIT 1"
        return db.fetch_one(sql, (product_id,))


class ProductImageModel:
    """商品图片模型 - 对应 product_images 表"""

    @staticmethod
    def create(product_id: int, image_url: str, image_type: str = "main", **kwargs) -> int:
        data = {"product_id": product_id, "image_url": image_url, "image_type": image_type}
        data.update(kwargs)
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO product_images ({fields}) VALUES ({placeholders})"
        return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def batch_create(product_id: int, images: list[dict]):
        if not images:
            return
        with db.transaction() as conn:
            for img in images:
                img["product_id"] = product_id
                fields = ", ".join(img.keys())
                placeholders = ", ".join(["%s"] * len(img))
                sql = f"INSERT INTO product_images ({fields}) VALUES ({placeholders})"
                db.execute(sql, tuple(img.values()), conn=conn)

    @staticmethod
    def get_by_product(product_id: int, image_type: str = None) -> list[dict]:
        sql = "SELECT * FROM product_images WHERE product_id = %s"
        params = [product_id]
        if image_type:
            sql += " AND image_type = %s"
            params.append(image_type)
        sql += " ORDER BY sort_order ASC"
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def delete_by_product(product_id: int):
        db.execute("DELETE FROM product_images WHERE product_id = %s", (product_id,))


class ReviewAnalysisModel:
    """评论分析结果模型 - 对应 review_analysis 表"""

    @staticmethod
    def save(product_id: int, analysis_type: str, data: dict) -> int:
        existing = db.fetch_one(
            "SELECT id FROM review_analysis WHERE product_id = %s AND analysis_type = %s",
            (product_id, analysis_type))
        # JSON 字段序列化
        for key in ("top_positive", "top_negative", "pain_points", "selling_points"):
            if key in data and isinstance(data[key], (list, dict)):
                data[key] = json.dumps(data[key])
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE review_analysis SET {set_clause}, analyzed_at = NOW() WHERE id = %s"
            db.execute(sql, (*data.values(), existing["id"]))
            return existing["id"]
        else:
            data["product_id"] = product_id
            data["analysis_type"] = analysis_type
            fields = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO review_analysis ({fields}) VALUES ({placeholders})"
            return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def get_by_product(product_id: int, analysis_type: str = None) -> list[dict]:
        sql = "SELECT * FROM review_analysis WHERE product_id = %s"
        params = [product_id]
        if analysis_type:
            sql += " AND analysis_type = %s"
            params.append(analysis_type)
        return db.fetch_all(sql, tuple(params))


class DetailPageAnalysisModel:
    """详情页分析模型 - 对应 detail_page_analysis 表"""

    @staticmethod
    def save(product_id: int, data: dict) -> int:
        # JSON 字段序列化
        for key in ("seo_keywords", "improvement"):
            if key in data and isinstance(data[key], (list, dict)):
                data[key] = json.dumps(data[key])
        existing = db.fetch_one(
            "SELECT id FROM detail_page_analysis WHERE product_id = %s", (product_id,))
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE detail_page_analysis SET {set_clause}, analyzed_at = NOW() WHERE id = %s"
            db.execute(sql, (*data.values(), existing["id"]))
            return existing["id"]
        else:
            data["product_id"] = product_id
            fields = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO detail_page_analysis ({fields}) VALUES ({placeholders})"
            return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def get_by_product(product_id: int) -> Optional[dict]:
        return db.fetch_one(
            "SELECT * FROM detail_page_analysis WHERE product_id = %s", (product_id,))


class ProfitAnalysisModel:
    """利润分析模型 - 对应 profit_analysis 表（增强版，替代 ProfitModel）"""

    @staticmethod
    def save(product_id: int, data: dict):
        existing = db.fetch_one(
            "SELECT id FROM profit_analysis WHERE product_id = %s", (product_id,))
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE profit_analysis SET {set_clause}, calculated_at = NOW() WHERE id = %s"
            db.execute(sql, (*data.values(), existing["id"]))
        else:
            data["product_id"] = product_id
            fields = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO profit_analysis ({fields}) VALUES ({placeholders})"
            db.execute(sql, tuple(data.values()))

    @staticmethod
    def get_by_product(product_id: int) -> Optional[dict]:
        return db.fetch_one(
            "SELECT * FROM profit_analysis WHERE product_id = %s", (product_id,))

    @staticmethod
    def get_profitable(min_margin: float = 20.0, limit: int = 50) -> list[dict]:
        """获取利润率高于指定值的产品"""
        sql = """SELECT pa.*, p.product_name, p.brand FROM profit_analysis pa
                 JOIN products p ON pa.product_id = p.id
                 WHERE pa.profit_margin >= %s ORDER BY pa.profit_margin DESC LIMIT %s"""
        return db.fetch_all(sql, (min_margin, limit))


class TrendDataModel:
    """趋势数据模型 - 对应 trend_data 表"""

    @staticmethod
    def batch_insert(keyword: str, platform: str, data_points: list[dict]):
        """批量插入趋势数据"""
        if not data_points:
            return
        sql = """INSERT INTO trend_data (keyword, platform, trend_date, interest_value, region, raw_data)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        with db.transaction() as conn:
            for dp in data_points:
                raw = json.dumps(dp.get("raw_data")) if dp.get("raw_data") else None
                db.execute(sql, (keyword, platform, dp["trend_date"],
                                 dp.get("interest_value"), dp.get("region"), raw), conn=conn)

    @staticmethod
    def get_by_keyword(keyword: str, platform: str = None, days: int = 90) -> list[dict]:
        sql = """SELECT * FROM trend_data WHERE keyword = %s
                 AND trend_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"""
        params = [keyword, days]
        if platform:
            sql += " AND platform = %s"
            params.append(platform)
        sql += " ORDER BY trend_date ASC"
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_latest(keyword: str, platform: str) -> Optional[dict]:
        sql = """SELECT * FROM trend_data WHERE keyword = %s AND platform = %s
                 ORDER BY trend_date DESC LIMIT 1"""
        return db.fetch_one(sql, (keyword, platform))


class AnalysisReportModel:
    """分析报告模型 - 对应 analysis_reports 表"""

    @staticmethod
    def create(keyword_id: int, report_type: str, title: str, summary: str,
               full_report: dict, recommendation: str = None, confidence: float = None) -> int:
        sql = """INSERT INTO analysis_reports
                 (keyword_id, report_type, title, summary, full_report, recommendation, confidence)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (
            keyword_id, report_type, title, summary,
            json.dumps(full_report), recommendation, confidence))

    @staticmethod
    def get_by_id(report_id: int) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM analysis_reports WHERE id = %s", (report_id,))

    @staticmethod
    def get_by_keyword(keyword_id: int) -> list[dict]:
        sql = "SELECT * FROM analysis_reports WHERE keyword_id = %s ORDER BY generated_at DESC"
        return db.fetch_all(sql, (keyword_id,))

    @staticmethod
    def get_recent(limit: int = 20) -> list[dict]:
        sql = "SELECT * FROM analysis_reports ORDER BY generated_at DESC LIMIT %s"
        return db.fetch_all(sql, (limit,))

    @staticmethod
    def get_by_recommendation(recommendation: str) -> list[dict]:
        sql = """SELECT * FROM analysis_reports WHERE recommendation = %s
                 ORDER BY confidence DESC"""
        return db.fetch_all(sql, (recommendation,))


class ProfitCalculationModel:
    """利润计算记录模型 - 对应 profit_calculations 表"""

    @staticmethod
    def create(user_id: int, input_data: dict, result_data: dict,
               asin: str = None, product_name: str = None) -> int:
        sql = """INSERT INTO profit_calculations (user_id, asin, product_name, input_data, result_data)
                 VALUES (%s, %s, %s, %s, %s)"""
        return db.insert_and_get_id(sql, (
            user_id, asin, product_name,
            json.dumps(input_data), json.dumps(result_data)))

    @staticmethod
    def get_by_user(user_id: int, page: int = 1, per_page: int = 20) -> list[dict]:
        offset = (page - 1) * per_page
        sql = """SELECT * FROM profit_calculations WHERE user_id = %s
                 ORDER BY created_at DESC LIMIT %s OFFSET %s"""
        return db.fetch_all(sql, (user_id, per_page, offset))

    @staticmethod
    def get_by_asin(user_id: int, asin: str) -> list[dict]:
        sql = """SELECT * FROM profit_calculations WHERE user_id = %s AND asin = %s
                 ORDER BY created_at DESC"""
        return db.fetch_all(sql, (user_id, asin))


class Asset3DModel:
    """3D 资产模型 - 对应 assets_3d 表"""

    @staticmethod
    def create(user_id: int, source_image: str = None, asin: str = None,
               provider: str = "triposr") -> str:
        """创建 3D 资产记录，返回资产 UUID"""
        asset_id = str(uuid.uuid4())
        sql = """INSERT INTO assets_3d (id, user_id, asin, source_image, provider)
                 VALUES (%s, %s, %s, %s, %s)"""
        db.execute(sql, (asset_id, user_id, asin, source_image, provider))
        return asset_id

    @staticmethod
    def get_by_id(asset_id: str) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM assets_3d WHERE id = %s", (asset_id,))

    @staticmethod
    def get_by_user(user_id: int, status: str = None, page: int = 1,
                    per_page: int = 20) -> list[dict]:
        offset = (page - 1) * per_page
        sql = "SELECT * FROM assets_3d WHERE user_id = %s"
        params = [user_id]
        if status:
            sql += " AND status = %s"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def update_status(asset_id: str, status: str, **kwargs):
        """更新资产状态和 URL"""
        data = {"status": status}
        data.update(kwargs)
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE assets_3d SET {set_clause} WHERE id = %s"
        db.execute(sql, (*data.values(), asset_id))

    @staticmethod
    def complete(asset_id: str, model_url: str, thumbnail_url: str = None,
                 video_url: str = None, metadata: dict = None):
        """标记 3D 资产生成完成"""
        sql = """UPDATE assets_3d SET status = 'completed', model_url = %s,
                 thumbnail_url = %s, video_url = %s, metadata = %s WHERE id = %s"""
        db.execute(sql, (model_url, thumbnail_url, video_url,
                         json.dumps(metadata) if metadata else None, asset_id))

    @staticmethod
    def get_by_asin(user_id: int, asin: str) -> list[dict]:
        sql = "SELECT * FROM assets_3d WHERE user_id = %s AND asin = %s ORDER BY created_at DESC"
        return db.fetch_all(sql, (user_id, asin))

    @staticmethod
    def count_by_user(user_id: int) -> int:
        result = db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM assets_3d WHERE user_id = %s", (user_id,))
        return result["cnt"] if result else 0
