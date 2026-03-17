"""
Amazon 前端搜索爬虫

当用户没有 SP-API 凭证时，通过解析亚马逊前端页面获取搜索结果。
支持: 关键词搜索、Top N 产品提取、分页爬取。
"""

import re
import json
import time
from typing import Optional
from urllib.parse import quote_plus

from utils.logger import get_logger
from utils.http_client import HttpClient

logger = get_logger()

# Amazon 各站点域名映射
AMAZON_DOMAINS = {
    "US": "www.amazon.com",
    "UK": "www.amazon.co.uk",
    "DE": "www.amazon.de",
    "FR": "www.amazon.fr",
    "IT": "www.amazon.it",
    "ES": "www.amazon.es",
    "JP": "www.amazon.co.jp",
    "CA": "www.amazon.ca",
    "AU": "www.amazon.com.au",
    "MX": "www.amazon.com.mx",
    "AE": "www.amazon.ae",
    "SG": "www.amazon.sg",
}


class AmazonSearchCrawler:
    """
    Amazon 前端搜索结果爬虫

    通过解析亚马逊搜索结果页面的 HTML/JSON，提取产品列表数据。
    支持多站点、分页爬取和反爬策略。
    """

    def __init__(self, http_client: HttpClient = None, marketplace: str = "US"):
        self.http_client = http_client or HttpClient()
        self.marketplace = marketplace.upper()
        self.domain = AMAZON_DOMAINS.get(self.marketplace, AMAZON_DOMAINS["US"])
        self.base_url = f"https://{self.domain}"

    def search(self, keyword: str, max_products: int = 100,
               sort_by: str = "relevanceblender") -> list[dict]:
        """
        搜索关键词并提取 Top N 产品数据。

        :param keyword: 搜索关键词
        :param max_products: 最大抓取数量
        :param sort_by: 排序方式
            - relevanceblender: 相关性（默认）
            - price-asc-rank: 价格从低到高
            - price-desc-rank: 价格从高到低
            - review-rank: 评论数
            - date-desc-rank: 最新上架
        :return: 产品列表
        """
        all_products = []
        page = 1
        max_pages = (max_products // 16) + 2  # 每页约 16-48 个产品

        logger.info(f"[Amazon搜索] 开始搜索: '{keyword}' | 站点: {self.marketplace} | 目标: {max_products}个")

        while len(all_products) < max_products and page <= max_pages:
            url = self._build_search_url(keyword, page, sort_by)

            try:
                html = self.http_client.get(url)
                if not html:
                    logger.warning(f"[Amazon搜索] 第{page}页获取失败，跳过")
                    break

                products = self._parse_search_results(html)
                if not products:
                    logger.info(f"[Amazon搜索] 第{page}页无更多结果")
                    break

                # 为每个产品添加排名信息
                for i, product in enumerate(products):
                    product["rank_position"] = len(all_products) + i + 1
                    product["search_keyword"] = keyword
                    product["marketplace"] = self.marketplace

                all_products.extend(products)
                logger.info(f"[Amazon搜索] 第{page}页: 获取 {len(products)} 个产品 | 累计: {len(all_products)}")

                page += 1
                time.sleep(2)  # 防止触发反爬

            except Exception as e:
                logger.error(f"[Amazon搜索] 第{page}页异常: {e}")
                break

        result = all_products[:max_products]
        logger.info(f"[Amazon搜索] 搜索完成: '{keyword}' | 共获取 {len(result)} 个产品")
        return result

    def _build_search_url(self, keyword: str, page: int, sort_by: str) -> str:
        """构建搜索 URL"""
        encoded_kw = quote_plus(keyword)
        url = f"{self.base_url}/s?k={encoded_kw}&s={sort_by}&page={page}"
        return url

    def _parse_search_results(self, html: str) -> list[dict]:
        """
        解析搜索结果页面 HTML，提取产品数据。
        优先尝试从嵌入的 JSON 数据中提取，回退到 HTML 解析。
        """
        products = []

        # 方法1: 尝试从页面内嵌 JSON 提取
        json_products = self._extract_from_embedded_json(html)
        if json_products:
            return json_products

        # 方法2: HTML 解析（BeautifulSoup）
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # 搜索结果容器
            result_divs = soup.select('[data-component-type="s-search-result"]')

            for div in result_divs:
                try:
                    product = self._parse_single_result(div)
                    if product and product.get("asin"):
                        products.append(product)
                except Exception as e:
                    logger.debug(f"[Amazon搜索] 解析单个产品失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"[Amazon搜索] HTML 解析失败: {e}")

        return products

    def _parse_single_result(self, div) -> Optional[dict]:
        """解析单个搜索结果 div 元素"""
        asin = div.get("data-asin", "")
        if not asin or asin.startswith("B0") is False and len(asin) != 10:
            # 跳过广告或无效 ASIN
            if not asin:
                return None

        # 标题
        title_elem = div.select_one("h2 a span") or div.select_one("h2 span")
        title = title_elem.get_text(strip=True) if title_elem else ""

        # 链接
        link_elem = div.select_one("h2 a")
        link = ""
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            link = f"{self.base_url}{href}" if href.startswith("/") else href

        # 主图
        img_elem = div.select_one("img.s-image")
        main_image = img_elem.get("src", "") if img_elem else ""

        # 价格
        price = self._extract_price(div)

        # 星级评分
        rating = 0.0
        rating_elem = div.select_one('[aria-label*="out of"]') or div.select_one("i.a-icon-star-small")
        if rating_elem:
            rating_text = rating_elem.get("aria-label", "") or rating_elem.get_text()
            rating_match = re.search(r"([\d.]+)\s*out of", rating_text)
            if rating_match:
                rating = float(rating_match.group(1))

        # 评论数
        review_count = 0
        review_elem = div.select_one('[aria-label*="rating"]')
        if review_elem:
            # 尝试从相邻元素获取评论数
            count_elem = review_elem.find_next("span", {"aria-label": True})
            if count_elem:
                count_text = count_elem.get("aria-label", "")
                count_match = re.search(r"([\d,]+)", count_text)
                if count_match:
                    review_count = int(count_match.group(1).replace(",", ""))
        # 备选方案
        if review_count == 0:
            count_spans = div.select('span[aria-label]')
            for span in count_spans:
                label = span.get("aria-label", "")
                if re.match(r"^[\d,]+$", label.strip()):
                    review_count = int(label.strip().replace(",", ""))
                    break

        # 品牌
        brand = ""
        brand_elem = div.select_one(".a-size-base-plus.a-color-base") or div.select_one(
            'span.a-size-base:not([aria-label])')
        if brand_elem:
            brand = brand_elem.get_text(strip=True)

        # 是否 Prime
        is_prime = bool(div.select_one("i.a-icon-prime"))

        # 是否赞助（广告）
        is_sponsored = bool(
            div.select_one('[data-component-type="sp-sponsored-result"]')
            or div.find(string=re.compile(r"Sponsored|赞助", re.I))
        )

        # BSR（搜索结果页通常不包含，需要详情页获取）
        # 但有时候 Amazon 会在搜索结果中显示 "Best Seller" 标签
        is_best_seller = bool(div.select_one(".a-badge-text"))

        return {
            "asin": asin,
            "title": title,
            "url": link or f"{self.base_url}/dp/{asin}",
            "main_image": main_image,
            "price": price,
            "rating": rating,
            "review_count": review_count,
            "brand": brand,
            "is_prime": is_prime,
            "is_sponsored": is_sponsored,
            "is_best_seller": is_best_seller,
            "source": "web-scraper",
            "platform": "amazon",
        }

    def _extract_price(self, div) -> Optional[float]:
        """从搜索结果中提取价格"""
        # 方法1: 整数+小数部分
        whole = div.select_one("span.a-price-whole")
        fraction = div.select_one("span.a-price-fraction")
        if whole:
            whole_text = whole.get_text(strip=True).replace(",", "").replace(".", "")
            frac_text = fraction.get_text(strip=True) if fraction else "00"
            try:
                return float(f"{whole_text}.{frac_text}")
            except ValueError:
                pass

        # 方法2: 完整价格字符串
        price_elem = div.select_one("span.a-price span.a-offscreen")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r"[\d,.]+", price_text)
            if price_match:
                try:
                    return float(price_match.group().replace(",", ""))
                except ValueError:
                    pass

        return None

    def _extract_from_embedded_json(self, html: str) -> list[dict]:
        """
        尝试从页面嵌入的 JavaScript JSON 数据中提取产品信息。
        Amazon 部分页面会在 script 标签中嵌入结构化数据。
        """
        products = []
        try:
            # 查找 data-search-metadata 或 s-main-slot 中的 JSON
            patterns = [
                r'"asin"\s*:\s*"(B[\dA-Z]{9})"',
            ]

            asins_found = set()
            for pattern in patterns:
                for match in re.finditer(pattern, html):
                    asins_found.add(match.group(1))

            # 如果找到了 ASIN，尝试提取更多数据
            # 这里仅作为辅助，主要还是靠 HTML 解析
            if len(asins_found) > 20:
                logger.debug(f"[Amazon搜索] 从嵌入JSON发现 {len(asins_found)} 个ASIN")

        except Exception as e:
            logger.debug(f"[Amazon搜索] JSON提取失败: {e}")

        return products  # 返回空列表，回退到 HTML 解析

    def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client:
            self.http_client.close()
