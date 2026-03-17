"""
Coupang 选品系统 - 前台搜索列表爬虫
功能: 根据关键词搜索Coupang，抓取前N名产品的基础信息
"""

import re
import json
import math
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t

logger = get_logger()

COUPANG_BASE_URL = "https://www.coupang.com"
SEARCH_URL = f"{COUPANG_BASE_URL}/np/search"
PRODUCTS_PER_PAGE = 36  # Coupang 每页约36个产品


class CoupangSearchCrawler:
    """
    Coupang 前台搜索爬虫
    输入关键词 → 爬取搜索结果列表 → 提取产品基础信息
    """

    def __init__(self, http_client: Optional[HttpClient] = None):
        self.client = http_client or HttpClient(min_delay=2.0, max_delay=5.0)

    def search(self, keyword: str, top_n: int = 50) -> list[dict]:
        """
        搜索关键词并返回前N个产品的基础信息

        :param keyword: 搜索关键词（韩文）
        :param top_n: 需要获取的产品数量
        :return: 产品列表 [{"coupang_product_id", "title", "url", "price", ...}, ...]
        """
        logger.info(t("crawler.start_search", keyword=keyword))
        all_products = []
        total_pages = math.ceil(top_n / PRODUCTS_PER_PAGE)

        for page in range(1, total_pages + 1):
            logger.info(t("crawler.crawling_page", page=page))
            products = self._crawl_search_page(keyword, page)

            if not products:
                logger.warning(f"Page {page}: No products found, stopping.")
                break

            all_products.extend(products)

            if len(all_products) >= top_n:
                break

        # 截取到指定数量并添加排名
        all_products = all_products[:top_n]
        for i, product in enumerate(all_products, 1):
            product["ranking"] = i

        logger.info(t("crawler.crawl_complete", count=len(all_products)))
        return all_products

    def _crawl_search_page(self, keyword: str, page: int) -> list[dict]:
        """爬取搜索结果的单页"""
        params = {
            "q": keyword,
            "page": page,
            "sorter": "scoreDesc",  # 按综合排序
            "listSize": PRODUCTS_PER_PAGE,
        }

        resp = self.client.get(SEARCH_URL, params=params)
        if not resp:
            return []

        return self._parse_search_page(resp.text)

    def _parse_search_page(self, html: str) -> list[dict]:
        """解析搜索结果页面HTML"""
        soup = BeautifulSoup(html, "lxml")
        products = []

        # Coupang 搜索结果的产品列表
        product_items = soup.select("li.search-product")
        if not product_items:
            # 备用选择器
            product_items = soup.select("ul#productList > li")

        for item in product_items:
            try:
                product = self._parse_product_item(item)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Parse product item error: {e}")
                continue

        return products

    def _parse_product_item(self, item) -> Optional[dict]:
        """解析单个产品条目"""
        product = {}

        # 产品ID和链接
        link_tag = item.select_one("a.search-product-link")
        if not link_tag:
            link_tag = item.select_one("a[href*='/vp/products/']")
        if not link_tag:
            return None

        href = link_tag.get("href", "")
        product["url"] = f"{COUPANG_BASE_URL}{href}" if href.startswith("/") else href

        # 从URL提取产品ID
        product_id_match = re.search(r'/products/(\d+)', href)
        if product_id_match:
            product["coupang_product_id"] = product_id_match.group(1)
        else:
            # 尝试从data属性获取
            product["coupang_product_id"] = item.get("data-product-id", "")

        if not product["coupang_product_id"]:
            return None

        # 产品标题
        title_tag = item.select_one(".name, .search-product-name, [class*='name']")
        product["title"] = title_tag.get_text(strip=True) if title_tag else ""

        # 主图URL
        img_tag = item.select_one("img.search-product-wrap-img, img[src*='thumbnail']")
        if not img_tag:
            img_tag = item.select_one("img")
        if img_tag:
            src = img_tag.get("src", "") or img_tag.get("data-img-src", "")
            if src.startswith("//"):
                src = "https:" + src
            product["main_image_url"] = src

        # 价格
        price_tag = item.select_one(".price-value, [class*='price'] strong, .base-price")
        if price_tag:
            price_text = price_tag.get_text(strip=True).replace(",", "").replace("원", "")
            try:
                product["price"] = float(re.sub(r'[^\d.]', '', price_text))
            except ValueError:
                product["price"] = None

        # 原价（划线价）
        original_price_tag = item.select_one(".base-price, [class*='origin-price']")
        if original_price_tag and original_price_tag != price_tag:
            orig_text = original_price_tag.get_text(strip=True).replace(",", "").replace("원", "")
            try:
                product["original_price"] = float(re.sub(r'[^\d.]', '', orig_text))
            except ValueError:
                product["original_price"] = None

        # 评分
        rating_tag = item.select_one(".rating, [class*='rating']")
        if rating_tag:
            rating_text = rating_tag.get_text(strip=True)
            try:
                product["rating"] = float(re.search(r'[\d.]+', rating_text).group())
            except (ValueError, AttributeError):
                product["rating"] = None

        # 评论数
        review_tag = item.select_one(".rating-total-count, [class*='review-count']")
        if review_tag:
            review_text = review_tag.get_text(strip=True).replace(",", "")
            try:
                product["review_count"] = int(re.search(r'\d+', review_text).group())
            except (ValueError, AttributeError):
                product["review_count"] = 0

        # 品牌名
        brand_tag = item.select_one("[class*='brand'], .brand-name")
        if brand_tag:
            product["brand_name"] = brand_tag.get_text(strip=True)

        # 配送方式标识
        product["delivery_type"] = self._detect_delivery_type(item)

        return product

    def _detect_delivery_type(self, item) -> str:
        """检测配送方式"""
        item_html = str(item)
        item_text = item.get_text()

        if "rocket-icon" in item_html or "로켓배송" in item_text:
            # 进一步区分蓝/橙/紫火箭
            if "로켓직구" in item_text or "rocket-direct" in item_html:
                return "purple_rocket"
            elif "로켓그로스" in item_text or "rocket-growth" in item_html:
                return "orange_rocket"
            else:
                return "blue_rocket"
        elif "판매자배송" in item_text or "seller-delivery" in item_html:
            return "self_delivery"

        return "unknown"

    def close(self):
        """关闭HTTP客户端"""
        self.client.close()
