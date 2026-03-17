"""
Coupang 选品系统 - 数据库配置
支持从环境变量或 .env 文件读取配置
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库连接配置"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "3306"))
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "")
    database: str = os.getenv("DB_NAME", "coupang_selection")
    charset: str = "utf8mb4"

    @property
    def connection_url(self) -> str:
        """返回 SQLAlchemy 格式的连接字符串"""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?charset={self.charset}"
        )

    @property
    def pymysql_config(self) -> dict:
        """返回 PyMySQL 直连参数"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
        }


# 全局配置实例
db_config = DatabaseConfig()
