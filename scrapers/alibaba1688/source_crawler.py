"""
Coupang 选品系统 - 1688 货源搜索爬虫
功能:
  1. 以图搜货：上传产品主图到1688搜索相似货源
  2. 关键词搜货：通过中文关键词搜索
  3. 提取货源价格、起订量、运费等信息
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

ALIBABA_1688_BASE = "https://www.1688.com"
ALIBABA_SEARCH_URL = f"{ALIBABA_1688_BASE}/s/search"
ALIBABA_IMAGE_SEARCH_URL = "https://s.1688.com/youyuan/index.htm"


class Alibaba1688Crawler:
    """
    1688 货源搜索爬虫
    支持: 以图搜货 / 关键词搜索 / 价格提取
    """

    def __init__(self, http_client: Optional[HttpClient] = None):
        self.client = http_client or HttpClient(min_delay=2.0, max_delay=4.0)

    def search_by_keyword(self, keyword: str, max_results: int = 20) -> list[dict]:
        """
        通过关键词在1688搜索货源

        :param keyword: 中文搜索关键词
        :param max_results: 最大结果数
        :return: 货源列表
        """
        logger.info(t("profit.source_search"))

        params = {
            "keywords": keyword,
            "n": "y",
            "spm": "a26352.13672862.searchbox.input",
        }

        resp = self.client.get(ALIBABA_SEARCH_URL, params=params)
        if not resp:
            return []

        sources = self._parse_search_results(resp.text)
        sources = sources[:max_results]

        logger.info(t("profit.source_found", count=len(sources)))
        return sources

    def search_by_image(self, image_path: str, max_results: int = 20) -> list[dict]:
        """
        以图搜货：上传图片到1688搜索相似产品

        :param image_path: 本地图片路径
        :param max_results: 最大结果数
        :return: 货源列表
        """
        logger.info(t("profit.source_search"))

        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return []

        # 上传图片
        try:
            with open(image_path, "rb") as f:
                files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
                resp = self.client.session.post(
                    ALIBABA_IMAGE_SEARCH_URL,
                    files=files,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30,
                )

            if resp and resp.status_code == 200:
                sources = self._parse_search_results(resp.text)
                sources = sources[:max_results]
                logger.info(t("profit.source_found", count=len(sources)))
                return sources

        except Exception as e:
            logger.error(f"Image search error: {e}")

        return []

    def _parse_search_results(self, html: str) -> list[dict]:
        """解析1688搜索结果页面"""
        soup = BeautifulSoup(html, "lxml")
        sources = []

        # 1688 产品卡片
        items = soup.select(
            ".sm-offer-item, "
            "[class*='offer-list'] [class*='item'], "
            ".normalcommon-offer-card"
        )

        for item in items:
            try:
                source = self._parse_source_item(item)
                if source:
                    sources.append(source)
            except Exception as e:
                logger.debug(f"Parse 1688 item error: {e}")
                continue

        # 备用: 尝试从页面中的JSON数据提取
        if not sources:
            sources = self._extract_from_json(html)

        return sources

    def _parse_source_item(self, item) -> Optional[dict]:
        """解析单个1688货源条目"""
        source = {}

        # 标题和链接
        title_tag = item.select_one("a[title], .title a, [class*='title'] a")
        if title_tag:
            source["title"] = title_tag.get("title", "") or title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            source["url"] = href
        else:
            return None

        # 价格
        price_tag = item.select_one(".sm-offer-priceNum, [class*='price'] em, .price")
        if price_tag:
            price_text = price_tag.get_text(strip=True).replace(",", "")
            try:
                source["price_rmb"] = float(re.search(r'[\d.]+', price_text).group())
            except (ValueError, AttributeError):
                source["price_rmb"] = None

        # 价格区间（1688通常有阶梯价）
        price_range_tags = item.select("[class*='price'] em, .price-num")
        if len(price_range_tags) >= 2:
            try:
                prices = []
                for pt in price_range_tags:
                    p = float(re.search(r'[\d.]+', pt.get_text(strip=True)).group())
                    prices.append(p)
                source["price_min"] = min(prices)
                source["price_max"] = max(prices)
            except (ValueError, AttributeError):
                pass

        # 起订量
        moq_tag = item.select_one("[class*='moq'], [class*='min-order'], .sale-quantity")
        if moq_tag:
            moq_text = moq_tag.get_text(strip=True)
            match = re.search(r'(\d+)', moq_text)
            source["moq"] = int(match.group(1)) if match else 1

        # 供应商名称
        supplier_tag = item.select_one("[class*='company'], [class*='supplier'], .company-name a")
        if supplier_tag:
            source["supplier_name"] = supplier_tag.get_text(strip=True)

        # 供应商所在地
        location_tag = item.select_one("[class*='location'], [class*='address']")
        if location_tag:
            source["supplier_location"] = location_tag.get_text(strip=True)

        # 成交量/销量
        sales_tag = item.select_one("[class*='sale'], [class*='deal']")
        if sales_tag:
            sales_text = sales_tag.get_text(strip=True)
            match = re.search(r'[\d.]+', sales_text.replace(",", ""))
            if match:
                source["monthly_sales"] = match.group()

        # 图片
        img_tag = item.select_one("img")
        if img_tag:
            src = img_tag.get("src", "") or img_tag.get("data-src", "")
            if src.startswith("//"):
                src = "https:" + src
            source["image_url"] = src

        return source

    def _extract_from_json(self, html: str) -> list[dict]:
        """从页面嵌入的JSON数据中提取货源信息"""
        sources = []

        # 尝试匹配页面中的JSON数据
        patterns = [
            r'__INIT_DATA__\s*=\s*({.*?});',
            r'window\.__data__\s*=\s*({.*?});',
            r'"offerList"\s*:\s*(\[.*?\])',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    offers = self._find_offers_in_json(data)
                    for offer in offers:
                        source = {
                            "title": offer.get("title", offer.get("subject", "")),
                            "url": offer.get("detailUrl", offer.get("href", "")),
                            "price_rmb": offer.get("price", offer.get("priceStr", None)),
                            "supplier_name": offer.get("company", offer.get("sellerName", "")),
                            "image_url": offer.get("imageUrl", offer.get("imgUrl", "")),
                        }
                        if source.get("title"):
                            sources.append(source)
                except (json.JSONDecodeError, TypeError):
                    continue

        return sources

    def _find_offers_in_json(self, data, depth=0) -> list:
        """递归查找JSON中的offer列表"""
        if depth > 5:
            return []

        if isinstance(data, list):
            # 检查是否是offer列表
            if data and isinstance(data[0], dict) and any(k in data[0] for k in ["title", "subject", "detailUrl"]):
                return data
            for item in data:
                result = self._find_offers_in_json(item, depth + 1)
                if result:
                    return result

        elif isinstance(data, dict):
            for key in ["offerList", "offers", "items", "data"]:
                if key in data:
                    result = self._find_offers_in_json(data[key], depth + 1)
                    if result:
                        return result
            for value in data.values():
                if isinstance(value, (list, dict)):
                    result = self._find_offers_in_json(value, depth + 1)
                    if result:
                        return result

        return []

    def close(self):
        """关闭HTTP客户端"""
        self.client.close()
