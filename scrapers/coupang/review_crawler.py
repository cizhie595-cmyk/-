"""
Coupang 选品系统 - 评论爬虫
功能: 爬取产品的所有评论数据，支持分页、评分筛选
"""

import re
import json
import time
from typing import Optional
from bs4 import BeautifulSoup

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t

logger = get_logger()

COUPANG_BASE_URL = "https://www.coupang.com"
# Coupang 评论API（AJAX加载）
REVIEW_API_URL = f"{COUPANG_BASE_URL}/vp/product/reviews"


class CoupangReviewCrawler:
    """
    Coupang 评论爬虫
    支持: 全量评论抓取 / 按评分筛选 / 分页遍历
    """

    def __init__(self, http_client: Optional[HttpClient] = None):
        self.client = http_client or HttpClient(min_delay=1.5, max_delay=3.0)

    def crawl_reviews(self, product_id: str, max_pages: int = 50) -> list[dict]:
        """
        爬取产品的所有评论

        :param product_id: Coupang产品ID
        :param max_pages: 最大爬取页数（防止无限循环）
        :return: 评论列表
        """
        all_reviews = []
        page = 1

        while page <= max_pages:
            logger.info(t("crawler.crawling_reviews", page=page))
            reviews, has_next = self._crawl_review_page(product_id, page)

            if not reviews:
                break

            all_reviews.extend(reviews)
            logger.debug(f"Page {page}: {len(reviews)} reviews, total: {len(all_reviews)}")

            if not has_next:
                break

            page += 1

        logger.info(f"Reviews crawl complete: {len(all_reviews)} reviews for product {product_id}")
        return all_reviews

    def _crawl_review_page(self, product_id: str, page: int) -> tuple[list[dict], bool]:
        """
        爬取评论的单页

        :return: (评论列表, 是否有下一页)
        """
        # 方式1: 尝试AJAX API
        reviews = self._crawl_via_api(product_id, page)
        if reviews is not None:
            has_next = len(reviews) >= 10  # 每页通常10条
            return reviews, has_next

        # 方式2: 直接解析HTML页面
        url = f"{COUPANG_BASE_URL}/vp/products/{product_id}"
        params = {"reviewPage": page}
        resp = self.client.get(url, params=params)
        if not resp:
            return [], False

        reviews = self._parse_reviews_html(resp.text)
        has_next = len(reviews) >= 10
        return reviews, has_next

    def _crawl_via_api(self, product_id: str, page: int) -> Optional[list[dict]]:
        """通过AJAX API获取评论"""
        params = {
            "productId": product_id,
            "page": page,
            "size": 20,
            "sortBy": "DATE_DESC",
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        }

        resp = self.client.get(REVIEW_API_URL, params=params, headers=headers)
        if not resp:
            return None

        try:
            data = resp.json()
            if "reviews" in data or "data" in data:
                raw_reviews = data.get("reviews") or data.get("data", {}).get("reviews", [])
                return [self._parse_api_review(r) for r in raw_reviews]
        except (json.JSONDecodeError, KeyError):
            return None

        return None

    def _parse_api_review(self, raw: dict) -> dict:
        """解析API返回的单条评论"""
        return {
            "author": raw.get("userName", raw.get("nickName", "")),
            "rating": raw.get("rating", raw.get("star", 0)),
            "content": raw.get("content", raw.get("body", "")),
            "sku_attribute": raw.get("productOption", raw.get("optionName", "")),
            "review_date": raw.get("createdAt", raw.get("createDate", "")),
            "helpful_count": raw.get("helpfulCount", 0),
            "photos": raw.get("photos", raw.get("images", [])),
        }

    def _parse_reviews_html(self, html: str) -> list[dict]:
        """从HTML页面解析评论"""
        soup = BeautifulSoup(html, "lxml")
        reviews = []

        review_items = soup.select(
            ".sdp-review__article__list__review, "
            "[class*='review-list'] > article, "
            "[class*='review-item']"
        )

        for item in review_items:
            try:
                review = self._parse_single_review_html(item)
                if review:
                    reviews.append(review)
            except Exception as e:
                logger.debug(f"Parse review error: {e}")
                continue

        return reviews

    def _parse_single_review_html(self, item) -> Optional[dict]:
        """解析HTML中的单条评论"""
        review = {}

        # 评论者
        author_tag = item.select_one("[class*='name'], .review-author")
        review["author"] = author_tag.get_text(strip=True) if author_tag else ""

        # 评分（通常通过星星图标的数量或class来判断）
        rating_tag = item.select_one("[class*='rating'], .star-rating")
        if rating_tag:
            # 尝试从class中提取评分
            classes = " ".join(rating_tag.get("class", []))
            rating_match = re.search(r'rating-(\d)', classes)
            if rating_match:
                review["rating"] = int(rating_match.group(1))
            else:
                # 尝试从aria-label或文本中提取
                aria = rating_tag.get("aria-label", "")
                text_match = re.search(r'(\d)', aria or rating_tag.get_text())
                review["rating"] = int(text_match.group(1)) if text_match else 0
        else:
            # 计算填充星星数量
            filled_stars = item.select("[class*='star'][class*='fill'], .star.on")
            review["rating"] = len(filled_stars) if filled_stars else 0

        # 评论内容
        content_tag = item.select_one(
            ".sdp-review__article__list__review__content, "
            "[class*='review-content'], "
            "[class*='review-text']"
        )
        review["content"] = content_tag.get_text(strip=True) if content_tag else ""

        # SKU属性
        sku_tag = item.select_one("[class*='option'], [class*='variant']")
        review["sku_attribute"] = sku_tag.get_text(strip=True) if sku_tag else ""

        # 评论日期
        date_tag = item.select_one("[class*='date'], time")
        if date_tag:
            review["review_date"] = date_tag.get("datetime", "") or date_tag.get_text(strip=True)
        else:
            review["review_date"] = ""

        # 评论图片
        review_imgs = item.select("[class*='review-photo'] img, [class*='review-image'] img")
        review["photos"] = []
        for img in review_imgs:
            src = img.get("src", "") or img.get("data-src", "")
            if src.startswith("//"):
                src = "https:" + src
            if src:
                review["photos"].append(src)

        # 有用数
        helpful_tag = item.select_one("[class*='helpful'] [class*='count']")
        if helpful_tag:
            try:
                review["helpful_count"] = int(re.search(r'\d+', helpful_tag.get_text()).group())
            except (ValueError, AttributeError):
                review["helpful_count"] = 0

        return review if review.get("content") or review.get("rating") else None

    def detect_suspicious_reviews(self, reviews: list[dict]) -> list[dict]:
        """
        检测疑似刷单评论

        规则:
        1. 评论内容过短（< 5字符）且5星
        2. 同一天大量5星评论
        3. 评论内容高度重复
        """
        from collections import Counter, defaultdict

        # 统计日期分布
        date_counts = defaultdict(int)
        date_5star = defaultdict(int)
        content_counts = Counter()

        for r in reviews:
            date = str(r.get("review_date", ""))[:10]
            if date:
                date_counts[date] += 1
                if r.get("rating", 0) == 5:
                    date_5star[date] += 1
            content = r.get("content", "").strip()
            if content:
                content_counts[content] += 1

        # 标记疑似刷单
        for r in reviews:
            r["is_suspicious"] = False
            r["suspicious_reason"] = ""
            reasons = []

            content = r.get("content", "").strip()
            rating = r.get("rating", 0)
            date = str(r.get("review_date", ""))[:10]

            # 规则1: 内容过短且5星
            if rating == 5 and len(content) < 5:
                reasons.append("短评+满分")

            # 规则2: 单日5星评论异常多（>10条）
            if date and date_5star.get(date, 0) > 10:
                reasons.append(f"单日5星评论异常({date_5star[date]}条)")

            # 规则3: 内容完全重复
            if content and content_counts[content] > 2:
                reasons.append(f"内容重复({content_counts[content]}次)")

            if reasons:
                r["is_suspicious"] = True
                r["suspicious_reason"] = "; ".join(reasons)

        suspicious_count = sum(1 for r in reviews if r["is_suspicious"])
        logger.info(f"Suspicious reviews detected: {suspicious_count}/{len(reviews)}")

        return reviews

    def close(self):
        """关闭HTTP客户端"""
        self.client.close()
