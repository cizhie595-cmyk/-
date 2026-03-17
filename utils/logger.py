"""
Coupang 选品系统 - 日志配置
使用 loguru 提供统一的日志管理，支持多语言
"""

import os
import sys
from loguru import logger

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 移除默认处理器
logger.remove()

# 控制台输出（简洁格式，支持中韩文）
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
)

# 文件输出（详细格式，按天轮转）
logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",
    retention="30 days",
)

# 错误日志单独记录
logger.add(
    os.path.join(LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="60 days",
)


def get_logger():
    """获取全局日志实例"""
    return logger
