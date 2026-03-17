"""
Coupang 选品系统 - 产品详情页爬虫
功能: 爬取产品详情页的完整信息（图片、描述、规格、发货方式等）
"""

import re
import os
import json
from typing import Optional
from bs4 import BeautifulSoup

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t

logger = get_logger()

COUPANG_BASE_URL = "https://www.coupang.com"
IMAGE_SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "images")


class CoupangDetailCrawler:
    """
    Coupang 产品详情页爬虫
    输入产品URL → 爬取详情页 → 提取完整产品信息、图片、规格
    """

    def __init__(self, http_client: Optional[HttpClient] = None):
        self.client = http_client or HttpClient(min_delay=2.0, max_delay=5.0)

    def crawl_detail(self, product_url: str, product_id: str = "") -> Optional[dict]:
        """
        爬取产品详情页

        :param product_url: 产品页面URL
        :param product_id: 产品ID（用于图片保存目录）
        :return: 详情信息字典
        """
        logger.info(t("crawler.crawling_detail", title=product_url[:60]))

        resp = self.client.get(product_url)
        if not resp:
            return None

        return self._parse_detail_page(resp.text, product_id)

    def _parse_detail_page(self, html: str, product_id: str) -> dict:
        """解析详情页HTML"""
        soup = BeautifulSoup(html, "lxml")
        detail = {}

        # === 基础信息 ===
        # 标题
        title_tag = soup.select_one("h1.prod-buy-header__title, h2.prod-buy-header__title")
        detail["title"] = title_tag.get_text(strip=True) if title_tag else ""

        # 品牌
        brand_tag = soup.select_one("a.prod-brand-name, [class*='brand'] a")
        detail["brand_name"] = brand_tag.get_text(strip=True) if brand_tag else ""

        # 制造商
        manufacturer_tag = soup.select_one("[class*='manufacturer']")
        detail["manufacturer"] = manufacturer_tag.get_text(strip=True) if manufacturer_tag else ""

        # 价格
        price_tag = soup.select_one(".total-price strong, [class*='total-price'] strong")
        if price_tag:
            price_text = price_tag.get_text(strip=True).replace(",", "").replace("원", "")
            try:
                detail["price"] = float(re.sub(r'[^\d.]', '', price_text))
            except ValueError:
                detail["price"] = None

        # 原价
        orig_tag = soup.select_one(".origin-price, [class*='base-price']")
        if orig_tag:
            orig_text = orig_tag.get_text(strip=True).replace(",", "").replace("원", "")
            try:
                detail["original_price"] = float(re.sub(r'[^\d.]', '', orig_text))
            except ValueError:
                detail["original_price"] = None

        # 评分
        rating_tag = soup.select_one(".prod-buy-header__rating-score, [class*='rating'] .rating-score")
        if rating_tag:
            try:
                detail["rating"] = float(rating_tag.get_text(strip=True))
            except ValueError:
                detail["rating"] = None

        # 评论数
        review_count_tag = soup.select_one(".prod-buy-header__review-count, [class*='count']")
        if review_count_tag:
            text = review_count_tag.get_text(strip=True).replace(",", "")
            match = re.search(r'\d+', text)
            detail["review_count"] = int(match.group()) if match else 0

        # === 配送方式 ===
        detail["delivery_type"] = self._detect_delivery_type(soup)

        # === 类目路径 ===
        breadcrumbs = soup.select(".breadcrumb a, [class*='breadcrumb'] a")
        detail["category_path"] = [bc.get_text(strip=True) for bc in breadcrumbs if bc.get_text(strip=True)]

        # === 产品图片 ===
        detail["images"] = self._extract_images(soup)

        # === SKU / 选项信息 ===
        detail["sku_options"] = self._extract_sku_options(soup)

        # === 产品规格/属性 ===
        detail["specifications"] = self._extract_specifications(soup)

        # === 详情页图片（长图描述） ===
        detail["detail_images"] = self._extract_detail_images(soup)

        # === 卖家信息 ===
        seller_tag = soup.select_one("[class*='seller-name'], .prod-seller-name a")
        detail["seller_name"] = seller_tag.get_text(strip=True) if seller_tag else ""

        return detail

    def _detect_delivery_type(self, soup) -> str:
        """检测配送方式（蓝/橙/紫火箭 或 自发货）"""
        page_text = soup.get_text()
        page_html = str(soup)

        if "로켓직구" in page_text or "rocket-direct" in page_html:
            return "purple_rocket"
        elif "로켓그로스" in page_text or "rocket-growth" in page_html:
            return "orange_rocket"
        elif "로켓배송" in page_text or "rocket-delivery" in page_html:
            return "blue_rocket"
        elif "판매자배송" in page_text:
            return "self_delivery"

        return "unknown"

    def _extract_images(self, soup) -> list[dict]:
        """提取产品图片（主图 + SKU图）"""
        images = []

        # 主图和缩略图
        img_items = soup.select(".prod-image__item img, .prod-image__detail img, [class*='product-image'] img")
        for i, img in enumerate(img_items):
            src = img.get("src", "") or img.get("data-src", "")
            if src.startswith("//"):
                src = "https:" + src
            if src and "thumbnail" not in src.lower():
                images.append({
                    "url": src,
                    "type": "main" if i == 0 else "sku",
                    "sort_order": i,
                })

        return images

    def _extract_sku_options(self, soup) -> list[dict]:
        """提取SKU选项（颜色、尺寸等）"""
        options = []

        option_items = soup.select(".prod-option__item, [class*='option'] li")
        for item in option_items:
            option = {
                "name": item.get_text(strip=True),
                "value": item.get("data-value", ""),
                "image": "",
            }
            img = item.select_one("img")
            if img:
                src = img.get("src", "") or img.get("data-src", "")
                if src.startswith("//"):
                    src = "https:" + src
                option["image"] = src
            options.append(option)

        return options

    def _extract_specifications(self, soup) -> dict:
        """提取产品规格/属性表"""
        specs = {}

        spec_rows = soup.select(".prod-attr-item, [class*='attribute'] tr, [class*='spec'] tr")
        for row in spec_rows:
            key_tag = row.select_one("th, dt, .attr-key, td:first-child")
            val_tag = row.select_one("td, dd, .attr-value, td:last-child")
            if key_tag and val_tag:
                key = key_tag.get_text(strip=True)
                val = val_tag.get_text(strip=True)
                if key and val and key != val:
                    specs[key] = val

        return specs

    def _extract_detail_images(self, soup) -> list[str]:
        """提取详情页描述区域的图片（长图）"""
        detail_images = []

        # 详情页描述区域
        detail_section = soup.select_one(".product-detail-content, #productDetail, [class*='detail-item']")
        if detail_section:
            imgs = detail_section.select("img")
            for img in imgs:
                src = img.get("src", "") or img.get("data-src", "")
                if src.startswith("//"):
                    src = "https:" + src
                if src:
                    detail_images.append(src)

        return detail_images

    def download_product_images(self, product_id: str, images: list[dict], detail_images: list[str]) -> dict:
        """
        下载产品的所有图片到本地

        :param product_id: 产品ID
        :param images: 主图/SKU图列表
        :param detail_images: 详情页图片URL列表
        :return: {"main": [paths], "sku": [paths], "detail": [paths]}
        """
        logger.info(t("crawler.download_images"))
        save_dir = os.path.join(IMAGE_SAVE_DIR, str(product_id))
        os.makedirs(save_dir, exist_ok=True)

        saved = {"main": [], "sku": [], "detail": []}

        # 下载主图和SKU图
        for img in images:
            img_type = img.get("type", "main")
            idx = img.get("sort_order", 0)
            ext = self._get_image_ext(img["url"])
            filename = f"{img_type}_{idx}{ext}"
            filepath = os.path.join(save_dir, filename)

            if self.client.download_image(img["url"], filepath):
                saved[img_type].append(filepath)

        # 下载详情页图片
        for i, url in enumerate(detail_images):
            ext = self._get_image_ext(url)
            filename = f"detail_{i}{ext}"
            filepath = os.path.join(save_dir, filename)

            if self.client.download_image(url, filepath):
                saved["detail"].append(filepath)

        return saved

    def _get_image_ext(self, url: str) -> str:
        """从URL推断图片扩展名"""
        url_lower = url.lower().split("?")[0]
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            if url_lower.endswith(ext):
                return ext
        return ".jpg"

    def close(self):
        """关闭HTTP客户端"""
        self.client.close()
