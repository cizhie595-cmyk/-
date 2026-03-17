"""
Coupang 选品系统 - 卖家后台数据爬虫
功能: 模拟登录Coupang卖家后台(Wing)，匹配产品并抓取点击量、销量、曝光量等运营数据
"""

import re
import os
import json
import time
import csv
from typing import Optional
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t

logger = get_logger()

# Coupang Wing (卖家后台) 相关URL
WING_BASE_URL = "https://wing.coupang.com"
WING_LOGIN_URL = f"{WING_BASE_URL}/login"
WING_DASHBOARD_URL = f"{WING_BASE_URL}/dashboard"
WING_PRODUCT_API = f"{WING_BASE_URL}/api/v1/products"
WING_STATS_API = f"{WING_BASE_URL}/api/v1/stats"


class CoupangBackendCrawler:
    """
    Coupang 卖家后台(Wing)数据爬虫

    工作流程:
    1. 使用账号密码登录 Wing 后台
    2. 通过标题/链接搜索匹配前台产品
    3. 下载产品的点击量、销量、曝光量等运营数据
    4. 支持按日期范围导出数据
    """

    def __init__(self, http_client: Optional[HttpClient] = None):
        self.client = http_client or HttpClient(min_delay=1.0, max_delay=2.0)
        self.is_logged_in = False
        self._cookies = {}

    def login(self, username: str, password: str) -> bool:
        """
        登录 Coupang Wing 卖家后台

        :param username: 卖家账号
        :param password: 密码
        :return: 是否登录成功
        """
        logger.info(t("crawler.backend_login"))

        # Step 1: 获取登录页面的CSRF token
        login_page = self.client.get(WING_LOGIN_URL)
        if not login_page:
            logger.error(t("crawler.backend_login_failed", reason="Cannot access login page"))
            return False

        # 提取CSRF token
        csrf_token = self._extract_csrf_token(login_page.text)

        # Step 2: 提交登录表单
        login_data = {
            "username": username,
            "password": password,
            "_csrf": csrf_token,
        }

        resp = self.client.post(
            WING_LOGIN_URL,
            data=login_data,
            headers={"Referer": WING_LOGIN_URL}
        )

        if resp and (resp.status_code in (200, 302)):
            # 检查是否真正登录成功
            if self._verify_login():
                self.is_logged_in = True
                logger.info(t("crawler.backend_login_success"))
                return True

        logger.error(t("crawler.backend_login_failed", reason="Invalid credentials or 2FA required"))
        return False

    def login_with_cookies(self, cookies: dict) -> bool:
        """
        使用已有的Cookie登录（跳过密码登录）
        适用于: 从浏览器导出Cookie后直接使用

        :param cookies: Cookie字典
        :return: 是否登录成功
        """
        logger.info("Attempting login with cookies...")
        self._cookies = cookies
        for key, value in cookies.items():
            self.client.session.cookies.set(key, value)

        if self._verify_login():
            self.is_logged_in = True
            logger.info(t("crawler.backend_login_success"))
            return True

        logger.error(t("crawler.backend_login_failed", reason="Cookies expired"))
        return False

    def _verify_login(self) -> bool:
        """验证是否已登录"""
        resp = self.client.get(WING_DASHBOARD_URL, max_retries=1)
        if resp and "login" not in resp.url.lower():
            return True
        return False

    def _extract_csrf_token(self, html: str) -> str:
        """从页面中提取CSRF token"""
        match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
        if match:
            return match.group(1)
        match = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', html)
        if match:
            return match.group(1)
        return ""

    def match_products(self, front_products: list[dict]) -> list[dict]:
        """
        将前台爬取的产品与后台数据进行匹配

        :param front_products: 前台产品列表（需包含title和coupang_product_id）
        :return: 匹配后的产品列表（增加backend_product_id字段）
        """
        if not self.is_logged_in:
            logger.error("Not logged in to Wing backend")
            return front_products

        logger.info(t("crawler.backend_matching"))
        matched_count = 0

        for product in front_products:
            backend_id = self._search_backend_product(product)
            if backend_id:
                product["backend_product_id"] = backend_id
                matched_count += 1
            else:
                product["backend_product_id"] = None

        logger.info(t("crawler.backend_match_success", count=matched_count))
        return front_products

    def _search_backend_product(self, product: dict) -> Optional[str]:
        """
        在后台搜索匹配的产品

        匹配策略:
        1. 优先通过产品ID精确匹配
        2. 其次通过标题模糊搜索
        """
        product_id = product.get("coupang_product_id", "")

        # 策略1: 通过产品ID搜索
        if product_id:
            params = {"productId": product_id}
            resp = self.client.get(WING_PRODUCT_API, params=params)
            if resp:
                try:
                    data = resp.json()
                    items = data.get("data", {}).get("items", [])
                    if items:
                        return items[0].get("vendorItemId", items[0].get("productId"))
                except (json.JSONDecodeError, KeyError):
                    pass

        # 策略2: 通过标题搜索
        title = product.get("title", "")
        if title:
            # 取标题前30个字符作为搜索词
            search_term = title[:30]
            params = {"keyword": search_term, "pageSize": 5}
            resp = self.client.get(WING_PRODUCT_API, params=params)
            if resp:
                try:
                    data = resp.json()
                    items = data.get("data", {}).get("items", [])
                    # 选择最匹配的结果
                    for item in items:
                        if self._title_similarity(title, item.get("name", "")) > 0.6:
                            return item.get("vendorItemId", item.get("productId"))
                except (json.JSONDecodeError, KeyError):
                    pass

        return None

    def _title_similarity(self, title1: str, title2: str) -> float:
        """简单的标题相似度计算（基于共同字符比例）"""
        if not title1 or not title2:
            return 0.0
        set1 = set(title1.lower())
        set2 = set(title2.lower())
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union) if union else 0.0

    def get_product_stats(self, backend_product_id: str, days: int = 30) -> list[dict]:
        """
        获取产品的运营数据（点击量、销量、曝光量）

        :param backend_product_id: 后台产品ID
        :param days: 获取最近N天的数据
        :return: 每日数据列表
        """
        if not self.is_logged_in:
            logger.error("Not logged in to Wing backend")
            return []

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        params = {
            "vendorItemId": backend_product_id,
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "timeUnit": "DAY",
        }

        resp = self.client.get(WING_STATS_API, params=params)
        if not resp:
            return []

        try:
            data = resp.json()
            stats_list = data.get("data", {}).get("stats", [])
            return [
                {
                    "record_date": item.get("date", ""),
                    "daily_clicks": item.get("clicks", item.get("clickCount", 0)),
                    "daily_sales": item.get("sales", item.get("orderCount", 0)),
                    "daily_views": item.get("views", item.get("impressionCount", 0)),
                    "daily_revenue": item.get("revenue", item.get("salesAmount", 0)),
                }
                for item in stats_list
            ]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Parse stats error: {e}")
            return []

    def batch_get_stats(self, products: list[dict], days: int = 30) -> dict:
        """
        批量获取多个产品的运营数据

        :param products: 产品列表（需包含backend_product_id）
        :param days: 获取最近N天的数据
        :return: {product_id: [daily_stats]}
        """
        all_stats = {}

        for product in products:
            backend_id = product.get("backend_product_id")
            if not backend_id:
                continue

            product_id = product.get("coupang_product_id", backend_id)
            stats = self.get_product_stats(backend_id, days)
            if stats:
                all_stats[product_id] = stats
                logger.debug(f"Got {len(stats)} days stats for product {product_id}")

        return all_stats

    def export_stats_csv(self, stats: dict, output_path: str):
        """
        将运营数据导出为CSV文件

        :param stats: {product_id: [daily_stats]}
        :param output_path: CSV输出路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "product_id", "date", "clicks", "sales", "views", "revenue"
            ])
            for product_id, daily_stats in stats.items():
                for day in daily_stats:
                    writer.writerow([
                        product_id,
                        day.get("record_date", ""),
                        day.get("daily_clicks", 0),
                        day.get("daily_sales", 0),
                        day.get("daily_views", 0),
                        day.get("daily_revenue", 0),
                    ])

        logger.info(f"Stats exported to: {output_path}")

    def close(self):
        """关闭HTTP客户端"""
        self.client.close()
