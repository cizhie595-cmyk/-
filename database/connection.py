"""
Coupang 选品系统 - 数据库连接管理器
提供连接池管理、自动重连、事务管理等功能
"""

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import sys
import os

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import db_config


class DatabaseManager:
    """数据库连接管理器"""

    def __init__(self):
        self._connection = None

    def get_connection(self):
        """获取数据库连接，支持自动重连"""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                **db_config.pymysql_config,
                cursorclass=DictCursor,
                autocommit=True,
            )
        return self._connection

    @contextmanager
    def transaction(self):
        """事务上下文管理器，自动提交或回滚"""
        conn = self.get_connection()
        conn.autocommit(False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit(True)

    def execute(self, sql: str, params=None) -> int:
        """执行写操作（INSERT/UPDATE/DELETE），返回受影响行数"""
        conn = self.get_connection()
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
            return affected

    def fetch_one(self, sql: str, params=None) -> dict | None:
        """查询单条记录"""
        conn = self.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def fetch_all(self, sql: str, params=None) -> list[dict]:
        """查询多条记录"""
        conn = self.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def insert_and_get_id(self, sql: str, params=None) -> int:
        """插入记录并返回自增ID"""
        conn = self.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid

    def close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None


# 全局数据库管理器实例
db = DatabaseManager()
