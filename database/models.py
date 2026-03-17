"""
Coupang 选品系统 - 数据模型层
封装各表的常用 CRUD 操作，供爬虫和分析模块调用
"""

import json
from datetime import date, datetime
from typing import Optional
from database.connection import db


class KeywordModel:
    """关键词模型"""

    @staticmethod
    def create(word: str, top_n: int = 50) -> int:
        sql = "INSERT INTO keywords (word, top_n) VALUES (%s, %s)"
        return db.insert_and_get_id(sql, (word, top_n))

    @staticmethod
    def update_status(keyword_id: int, status: str):
        sql = "UPDATE keywords SET status = %s WHERE id = %s"
        db.execute(sql, (status, keyword_id))

    @staticmethod
    def get_all() -> list[dict]:
        return db.fetch_all("SELECT * FROM keywords ORDER BY created_at DESC")


class ProductModel:
    """产品模型"""

    @staticmethod
    def create(data: dict) -> int:
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO products ({fields}) VALUES ({placeholders})"
        return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def upsert(coupang_product_id: str, data: dict) -> int:
        """根据 coupang_product_id 插入或更新"""
        existing = db.fetch_one(
            "SELECT id FROM products WHERE coupang_product_id = %s",
            (coupang_product_id,),
        )
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE products SET {set_clause} WHERE coupang_product_id = %s"
            db.execute(sql, (*data.values(), coupang_product_id))
            return existing["id"]
        else:
            data["coupang_product_id"] = coupang_product_id
            return ProductModel.create(data)

    @staticmethod
    def get_by_keyword(keyword_id: int, include_filtered: bool = False) -> list[dict]:
        sql = "SELECT * FROM products WHERE keyword_id = %s"
        if not include_filtered:
            sql += " AND is_filtered = 0"
        sql += " ORDER BY ranking ASC"
        return db.fetch_all(sql, (keyword_id,))

    @staticmethod
    def mark_filtered(product_id: int, reason: str = None):
        sql = "UPDATE products SET is_filtered = 1, filter_reason = %s WHERE id = %s"
        db.execute(sql, (reason, product_id))


class DailyMetricsModel:
    """每日运营数据模型"""

    @staticmethod
    def insert(product_id: int, record_date: date, clicks: int, sales: int, views: int):
        revenue = None  # 可后续计算
        conversion = sales / clicks if clicks > 0 else 0
        sql = """INSERT INTO daily_metrics
                 (product_id, record_date, daily_clicks, daily_sales, daily_views, conversion_rate)
                 VALUES (%s, %s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE
                 daily_clicks = VALUES(daily_clicks),
                 daily_sales = VALUES(daily_sales),
                 daily_views = VALUES(daily_views),
                 conversion_rate = VALUES(conversion_rate)"""
        db.execute(sql, (product_id, record_date, clicks, sales, views, conversion))

    @staticmethod
    def get_30d_summary(product_id: int) -> Optional[dict]:
        sql = """SELECT
                    SUM(daily_clicks) AS total_clicks,
                    SUM(daily_sales) AS total_sales,
                    SUM(daily_views) AS total_views,
                    AVG(conversion_rate) AS avg_conversion
                 FROM daily_metrics
                 WHERE product_id = %s
                   AND record_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"""
        return db.fetch_one(sql, (product_id,))


class ReviewModel:
    """评论模型"""

    @staticmethod
    def batch_insert(product_id: int, reviews: list[dict]):
        sql = """INSERT INTO product_reviews
                 (product_id, author, rating, content, sku_attribute, review_date)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        with db.transaction() as conn:
            with conn.cursor() as cursor:
                for r in reviews:
                    cursor.execute(sql, (
                        product_id,
                        r.get("author"),
                        r.get("rating"),
                        r.get("content"),
                        r.get("sku_attribute"),
                        r.get("review_date"),
                    ))

    @staticmethod
    def get_by_product(product_id: int, exclude_suspicious: bool = True) -> list[dict]:
        sql = "SELECT * FROM product_reviews WHERE product_id = %s"
        if exclude_suspicious:
            sql += " AND is_suspicious = 0"
        sql += " ORDER BY review_date DESC"
        return db.fetch_all(sql, (product_id,))


class ProfitModel:
    """利润分析模型"""

    @staticmethod
    def save(product_id: int, data: dict):
        existing = db.fetch_one(
            "SELECT id FROM profit_analysis WHERE product_id = %s", (product_id,)
        )
        if existing:
            set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
            sql = f"UPDATE profit_analysis SET {set_clause} WHERE product_id = %s"
            db.execute(sql, (*data.values(), product_id))
        else:
            data["product_id"] = product_id
            fields = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO profit_analysis ({fields}) VALUES ({placeholders})"
            db.execute(sql, tuple(data.values()))

    @staticmethod
    def get_by_product(product_id: int) -> Optional[dict]:
        return db.fetch_one(
            "SELECT * FROM profit_analysis WHERE product_id = %s", (product_id,)
        )
