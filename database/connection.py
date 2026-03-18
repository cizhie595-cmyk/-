"""
Coupang 选品系统 - 数据库连接管理器
提供: 连接池管理、自动重连、事务管理、健康检查
基于 DBUtils.PooledDB 实现高性能连接池
"""

import os
import sys
import threading
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import db_config

# 尝试导入连接池库
try:
    from dbutils.pooled_db import PooledDB
    POOL_AVAILABLE = True
except ImportError:
    POOL_AVAILABLE = False

# 日志（延迟导入避免循环依赖）
_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        try:
            from utils.logger import get_logger
            _logger = get_logger()
        except Exception:
            import logging
            _logger = logging.getLogger(__name__)
    return _logger


# 连接池配置
POOL_MIN_CACHED = int(os.getenv("DB_POOL_MIN_CACHED", "5"))
POOL_MAX_CACHED = int(os.getenv("DB_POOL_MAX_CACHED", "10"))
POOL_MAX_SHARED = int(os.getenv("DB_POOL_MAX_SHARED", "20"))
POOL_MAX_CONNECTIONS = int(os.getenv("DB_POOL_MAX_CONNECTIONS", "50"))
POOL_BLOCKING = True
POOL_MAX_USAGE = int(os.getenv("DB_POOL_MAX_USAGE", "0"))
POOL_PING = int(os.getenv("DB_POOL_PING", "1"))


class DatabaseManager:
    """
    数据库连接管理器

    优先使用 DBUtils 连接池，不可用时降级为单连接模式。
    所有公开方法保持向后兼容。
    """

    def __init__(self):
        self._pool = None
        self._connection = None
        self._lock = threading.Lock()
        self._pool_mode = False
        self._init_pool()

    def _init_pool(self):
        """初始化连接池"""
        logger = _get_logger()

        if not POOL_AVAILABLE:
            logger.warning(
                "[DB] DBUtils 未安装，使用单连接模式。"
                "建议安装: pip install DBUtils"
            )
            return

        try:
            self._pool = PooledDB(
                creator=pymysql,
                mincached=POOL_MIN_CACHED,
                maxcached=POOL_MAX_CACHED,
                maxshared=POOL_MAX_SHARED,
                maxconnections=POOL_MAX_CONNECTIONS,
                blocking=POOL_BLOCKING,
                maxusage=POOL_MAX_USAGE or None,
                ping=POOL_PING,
                cursorclass=DictCursor,
                **db_config.pymysql_config,
            )
            self._pool_mode = True
            logger.info(
                f"[DB] 连接池初始化成功: "
                f"min={POOL_MIN_CACHED}, max_cached={POOL_MAX_CACHED}, "
                f"max_shared={POOL_MAX_SHARED}, max_conn={POOL_MAX_CONNECTIONS}"
            )
        except Exception as e:
            logger.error(f"[DB] 连接池初始化失败，降级为单连接模式: {e}")
            self._pool = None
            self._pool_mode = False

    def get_connection(self):
        """获取数据库连接"""
        if self._pool_mode and self._pool:
            return self._pool.connection()

        with self._lock:
            if self._connection is None or not self._connection.open:
                try:
                    self._connection = pymysql.connect(
                        **db_config.pymysql_config,
                        cursorclass=DictCursor,
                        autocommit=True,
                    )
                except pymysql.Error as e:
                    _get_logger().error(f"[DB] 连接失败: {e}")
                    raise
            return self._connection

    @contextmanager
    def connection_context(self):
        """连接上下文管理器，自动获取和释放连接"""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            if self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass

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
            if self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute(self, sql: str, params=None, conn=None) -> int:
        """执行写操作（INSERT/UPDATE/DELETE），返回受影响行数"""
        own_conn = conn is None
        if own_conn:
            conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                return affected
        except pymysql.OperationalError as e:
            if own_conn and e.args[0] in (2006, 2013):
                _get_logger().warning(f"[DB] 连接断开，正在重试: {e}")
                conn = self._reconnect()
                with conn.cursor() as cursor:
                    return cursor.execute(sql, params)
            raise
        finally:
            if own_conn and self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass

    def fetch_one(self, sql: str, params=None, conn=None) -> dict | None:
        """查询单条记录"""
        own_conn = conn is None
        if own_conn:
            conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        except pymysql.OperationalError as e:
            if own_conn and e.args[0] in (2006, 2013):
                _get_logger().warning(f"[DB] 连接断开，正在重试: {e}")
                conn = self._reconnect()
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchone()
            raise
        finally:
            if own_conn and self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass

    def fetch_all(self, sql: str, params=None, conn=None) -> list[dict]:
        """查询多条记录"""
        own_conn = conn is None
        if own_conn:
            conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except pymysql.OperationalError as e:
            if own_conn and e.args[0] in (2006, 2013):
                _get_logger().warning(f"[DB] 连接断开，正在重试: {e}")
                conn = self._reconnect()
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
            raise
        finally:
            if own_conn and self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass

    def insert_and_get_id(self, sql: str, params=None, conn=None) -> int:
        """插入记录并返回自增ID"""
        own_conn = conn is None
        if own_conn:
            conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.lastrowid
        except pymysql.OperationalError as e:
            if own_conn and e.args[0] in (2006, 2013):
                _get_logger().warning(f"[DB] 连接断开，正在重试: {e}")
                conn = self._reconnect()
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.lastrowid
            raise
        finally:
            if own_conn and self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass

    def _reconnect(self):
        """重新建立连接（降级模式）"""
        with self._lock:
            try:
                if self._connection and self._connection.open:
                    self._connection.close()
            except Exception:
                pass
            self._connection = pymysql.connect(
                **db_config.pymysql_config,
                cursorclass=DictCursor,
                autocommit=True,
            )
            return self._connection

    def health_check(self) -> dict:
        """数据库健康检查"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            if self._pool_mode:
                try:
                    conn.close()
                except Exception:
                    pass
            return {
                "status": "ok",
                "pool_mode": self._pool_mode,
                "message": "数据库连接正常",
            }
        except Exception as e:
            return {
                "status": "error",
                "pool_mode": self._pool_mode,
                "message": f"数据库连接异常: {str(e)}",
            }

    def close(self):
        """关闭连接/连接池"""
        if self._pool_mode and self._pool:
            try:
                self._pool.close()
            except Exception:
                pass
            self._pool = None
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

    @property
    def is_pool_mode(self) -> bool:
        """是否使用连接池模式"""
        return self._pool_mode


# 全局数据库管理器实例
db = DatabaseManager()
