"""
Amazon 爬虫模块

支持:
  - SP-API 官方接口数据获取
  - 前端页面爬虫（关键词搜索、详情页、评论）
  - 后台搜索词报告解析
  - 第三方 API 集成（Keepa、Rainforest）
"""

from scrapers.amazon.search_crawler import AmazonSearchCrawler
from scrapers.amazon.detail_crawler import AmazonDetailCrawler
from scrapers.amazon.review_crawler import AmazonReviewCrawler
from scrapers.amazon.sp_api_client import AmazonSPAPIClient
from scrapers.amazon.backend_parser import AmazonBackendParser
from scrapers.amazon.third_party_api import KeepaClient, RainforestClient

__all__ = [
    "AmazonSearchCrawler",
    "AmazonDetailCrawler",
    "AmazonReviewCrawler",
    "AmazonSPAPIClient",
    "AmazonBackendParser",
    "KeepaClient",
    "RainforestClient",
]
