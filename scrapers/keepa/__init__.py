"""
Keepa API 集成模块

提供 Amazon 产品历史数据：
  - 价格历史曲线
  - BSR 排名历史
  - 评论数增长趋势
  - 销量预估
  - Buy Box 追踪
"""

from scrapers.keepa.keepa_client import KeepaClient

__all__ = ["KeepaClient"]
