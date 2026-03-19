"""
项目管理模型层
包含: SourcingProjectModel, ProjectProductModel, AnalysisTaskModel
对应表: sourcing_projects, project_products, analysis_tasks
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from database.connection import db


class SourcingProjectModel:
    """选品项目模型 - 对应 sourcing_projects 表"""

    @staticmethod
    def create(user_id: int, name: str, keyword: str, marketplace: str = "US",
               settings: dict = None) -> str:
        """创建项目，返回项目 UUID"""
        project_id = str(uuid.uuid4())
        sql = """INSERT INTO sourcing_projects (id, user_id, name, keyword, marketplace, settings)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        db.execute(sql, (project_id, user_id, name, keyword, marketplace,
                         json.dumps(settings) if settings else None))
        return project_id

    @staticmethod
    def get_by_id(project_id: str) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM sourcing_projects WHERE id = %s", (project_id,))

    @staticmethod
    def get_by_user(user_id: int, status: str = None, page: int = 1,
                    per_page: int = 20) -> list[dict]:
        """获取用户的项目列表"""
        offset = (page - 1) * per_page
        sql = "SELECT * FROM sourcing_projects WHERE user_id = %s"
        params = [user_id]
        if status:
            sql += " AND status = %s"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def update_status(project_id: str, status: str, product_count: int = None):
        """更新项目状态"""
        if product_count is not None:
            sql = "UPDATE sourcing_projects SET status = %s, product_count = %s WHERE id = %s"
            db.execute(sql, (status, product_count, project_id))
        else:
            sql = "UPDATE sourcing_projects SET status = %s WHERE id = %s"
            db.execute(sql, (status, project_id))

    @staticmethod
    def update_settings(project_id: str, settings: dict):
        sql = "UPDATE sourcing_projects SET settings = %s WHERE id = %s"
        db.execute(sql, (json.dumps(settings), project_id))

    @staticmethod
    def delete(project_id: str):
        """删除项目及其关联数据"""
        db.execute("DELETE FROM project_products WHERE project_id = %s", (project_id,))
        db.execute("DELETE FROM analysis_tasks WHERE project_id = %s", (project_id,))
        db.execute("DELETE FROM sourcing_projects WHERE id = %s", (project_id,))

    @staticmethod
    def count_by_user(user_id: int) -> int:
        result = db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM sourcing_projects WHERE user_id = %s", (user_id,))
        return result["cnt"] if result else 0


class ProjectProductModel:
    """项目产品模型 - 对应 project_products 表"""

    @staticmethod
    def create(project_id: str, asin: str, data: dict) -> int:
        """添加产品到项目"""
        data["project_id"] = project_id
        data["asin"] = asin
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO project_products ({fields}) VALUES ({placeholders})"
        return db.insert_and_get_id(sql, tuple(data.values()))

    @staticmethod
    def batch_create(project_id: str, products: list[dict]):
        """批量添加产品"""
        if not products:
            return
        with db.transaction() as conn:
            for p in products:
                p["project_id"] = project_id
                fields = ", ".join(p.keys())
                placeholders = ", ".join(["%s"] * len(p))
                sql = f"INSERT INTO project_products ({fields}) VALUES ({placeholders})"
                db.execute(sql, tuple(p.values()), conn=conn)

    @staticmethod
    def get_by_project(project_id: str, include_filtered: bool = False) -> list[dict]:
        sql = "SELECT * FROM project_products WHERE project_id = %s"
        if not include_filtered:
            sql += " AND is_filtered = 0"
        sql += " ORDER BY bsr ASC"
        return db.fetch_all(sql, (project_id,))

    @staticmethod
    def get_by_asin(project_id: str, asin: str) -> Optional[dict]:
        sql = "SELECT * FROM project_products WHERE project_id = %s AND asin = %s"
        return db.fetch_one(sql, (project_id, asin))

    @staticmethod
    def update(product_id: int, data: dict):
        if not data:
            return
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE project_products SET {set_clause} WHERE id = %s"
        db.execute(sql, (*data.values(), product_id))

    @staticmethod
    def mark_filtered(product_id: int, reason: str = None):
        sql = "UPDATE project_products SET is_filtered = 1, filter_reason = %s WHERE id = %s"
        db.execute(sql, (reason, product_id))

    @staticmethod
    def count_by_project(project_id: str, include_filtered: bool = False) -> int:
        sql = "SELECT COUNT(*) AS cnt FROM project_products WHERE project_id = %s"
        if not include_filtered:
            sql += " AND is_filtered = 0"
        result = db.fetch_one(sql, (project_id,))
        return result["cnt"] if result else 0


class AnalysisTaskModel:
    """分析任务模型 - 对应 analysis_tasks 表"""

    @staticmethod
    def create(user_id: int, task_type: str, project_id: str = None,
               target_asin: str = None) -> str:
        """创建分析任务，返回任务 UUID"""
        task_id = str(uuid.uuid4())
        sql = """INSERT INTO analysis_tasks (id, user_id, project_id, task_type, target_asin)
                 VALUES (%s, %s, %s, %s, %s)"""
        db.execute(sql, (task_id, user_id, project_id, task_type, target_asin))
        return task_id

    @staticmethod
    def get_by_id(task_id: str) -> Optional[dict]:
        return db.fetch_one("SELECT * FROM analysis_tasks WHERE id = %s", (task_id,))

    @staticmethod
    def get_by_project(project_id: str) -> list[dict]:
        sql = "SELECT * FROM analysis_tasks WHERE project_id = %s ORDER BY created_at DESC"
        return db.fetch_all(sql, (project_id,))

    @staticmethod
    def get_by_user(user_id: int, status: str = None, page: int = 1,
                    per_page: int = 20) -> list[dict]:
        offset = (page - 1) * per_page
        sql = "SELECT * FROM analysis_tasks WHERE user_id = %s"
        params = [user_id]
        if status:
            sql += " AND status = %s"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def update_status(task_id: str, status: str, progress: int = None):
        if progress is not None:
            sql = "UPDATE analysis_tasks SET status = %s, progress = %s WHERE id = %s"
            db.execute(sql, (status, progress, task_id))
        else:
            sql = "UPDATE analysis_tasks SET status = %s WHERE id = %s"
            db.execute(sql, (status, task_id))

    @staticmethod
    def complete(task_id: str, result: dict):
        """标记任务完成并保存结果"""
        sql = """UPDATE analysis_tasks SET status = 'completed', progress = 100,
                 result = %s, completed_at = NOW() WHERE id = %s"""
        db.execute(sql, (json.dumps(result), task_id))

    @staticmethod
    def fail(task_id: str, error_message: str):
        """标记任务失败"""
        sql = """UPDATE analysis_tasks SET status = 'failed',
                 error_message = %s, completed_at = NOW() WHERE id = %s"""
        db.execute(sql, (error_message, task_id))

    @staticmethod
    def set_celery_id(task_id: str, celery_task_id: str):
        sql = "UPDATE analysis_tasks SET celery_task_id = %s WHERE id = %s"
        db.execute(sql, (celery_task_id, task_id))
