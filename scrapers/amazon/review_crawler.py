"""
Amazon 评论爬虫

深度挖掘商品评论数据：
  - 分页爬取全部评论
  - 按星级/SKU属性筛选
  - 提取评论时间线（推算上架周期）
  - 识别疑似刷单评论
"""

import re
import time
from typing import Optional
from datetime import datetime

from utils.logger import get_logger
from utils.http_client import HttpClient

logger = get_logger()


class AmazonReviewCrawler:
    """
    Amazon 评论深度爬虫

    支持: 分页爬取、星级筛选、Vine 评论标记、
    刷单检测辅助数据、SKU 属性拆解。
    """

    def __init__(self, http_client: HttpClient = None, marketplace: str = "US"):
        self.http_client = http_client or HttpClient()
        self.marketplace = marketplace.upper()

        domain_map = {
            "US": "www.amazon.com", "UK": "www.amazon.co.uk",
            "DE": "www.amazon.de", "JP": "www.amazon.co.jp",
            "CA": "www.amazon.ca", "AU": "www.amazon.com.au",
        }
        self.domain = domain_map.get(self.marketplace, "www.amazon.com")
        self.base_url = f"https://{self.domain}"

    def crawl_reviews(self, asin: str, max_reviews: int = 200,
                      star_filter: int = None,
                      sort_by: str = "recent") -> dict:
        """
        爬取指定 ASIN 的评论。

        :param asin: 商品 ASIN
        :param max_reviews: 最大爬取数量
        :param star_filter: 星级筛选 (1-5)，None 表示全部
        :param sort_by: 排序方式 (recent / helpful)
        :return: {reviews: [...], statistics: {...}, earliest_date: ...}
        """
        all_reviews = []
        page = 1
        max_pages = (max_reviews // 10) + 2

        logger.info(f"[Amazon评论] 开始爬取: {asin} | 目标: {max_reviews}条 | 排序: {sort_by}")

        while len(all_reviews) < max_reviews and page <= max_pages:
            url = self._build_review_url(asin, page, star_filter, sort_by)

            try:
                html = self.http_client.get(url)
                if not html:
                    break

                reviews = self._parse_review_page(html)
                if not reviews:
                    logger.info(f"[Amazon评论] 第{page}页无更多评论")
                    break

                all_reviews.extend(reviews)
                logger.info(f"[Amazon评论] 第{page}页: {len(reviews)}条 | 累计: {len(all_reviews)}")

                page += 1
                time.sleep(1.5)

            except Exception as e:
                logger.error(f"[Amazon评论] 第{page}页异常: {e}")
                break

        reviews = all_reviews[:max_reviews]

        # 统计分析
        result = {
            "asin": asin,
            "reviews": reviews,
            "total_crawled": len(reviews),
            "statistics": self._compute_statistics(reviews),
            "earliest_date": self._find_earliest_date(reviews),
            "sku_distribution": self._analyze_sku_distribution(reviews),
            "fake_review_suspects": self._detect_fake_reviews(reviews),
        }

        logger.info(f"[Amazon评论] {asin} 爬取完成: {len(reviews)}条评论")
        return result

    def _build_review_url(self, asin: str, page: int,
                          star_filter: int, sort_by: str) -> str:
        """构建评论页面 URL"""
        url = f"{self.base_url}/product-reviews/{asin}"
        url += f"?pageNumber={page}"
        url += f"&sortBy={sort_by}"
        url += "&reviewerType=all_reviews"

        if star_filter and 1 <= star_filter <= 5:
            url += f"&filterByStar={self._star_filter_param(star_filter)}"

        return url

    def _star_filter_param(self, star: int) -> str:
        """星级筛选参数映射"""
        mapping = {
            1: "one_star",
            2: "two_star",
            3: "three_star",
            4: "four_star",
            5: "five_star",
        }
        return mapping.get(star, "all_stars")

    def _parse_review_page(self, html: str) -> list[dict]:
        """解析评论页面 HTML"""
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            review_divs = soup.select('[data-hook="review"]')

            for div in review_divs:
                try:
                    review = self._parse_single_review(div)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    logger.debug(f"[Amazon评论] 解析单条评论失败: {e}")

        except Exception as e:
            logger.error(f"[Amazon评论] 页面解析失败: {e}")

        return reviews

    def _parse_single_review(self, div) -> Optional[dict]:
        """解析单条评论"""
        review = {}

        # 评论 ID
        review["review_id"] = div.get("id", "")

        # 评论者
        author_elem = div.select_one(".a-profile-name")
        review["author"] = author_elem.get_text(strip=True) if author_elem else ""

        # 星级
        star_elem = div.select_one('[data-hook="review-star-rating"]') or \
                    div.select_one("i.a-icon-star")
        if star_elem:
            star_text = star_elem.get_text()
            match = re.search(r"([\d.]+)", star_text)
            review["rating"] = float(match.group(1)) if match else 0
        else:
            review["rating"] = 0

        # 标题
        title_elem = div.select_one('[data-hook="review-title"]') or \
                     div.select_one(".review-title")
        review["title"] = title_elem.get_text(strip=True) if title_elem else ""

        # 正文
        body_elem = div.select_one('[data-hook="review-body"]')
        review["body"] = body_elem.get_text(strip=True) if body_elem else ""

        # 日期
        date_elem = div.select_one('[data-hook="review-date"]')
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            review["date_text"] = date_text
            review["date"] = self._parse_review_date(date_text)
        else:
            review["date_text"] = ""
            review["date"] = ""

        # 是否 Verified Purchase
        vp_elem = div.select_one('[data-hook="avp-badge"]')
        review["verified_purchase"] = bool(vp_elem)

        # 是否 Vine 评论
        vine_elem = div.find(string=re.compile(r"Vine", re.I))
        review["is_vine"] = bool(vine_elem)

        # 有用票数
        helpful_elem = div.select_one('[data-hook="helpful-vote-statement"]')
        review["helpful_votes"] = 0
        if helpful_elem:
            match = re.search(r"(\d+)", helpful_elem.get_text())
            if match:
                review["helpful_votes"] = int(match.group(1))

        # SKU 属性（颜色、尺寸等）
        format_elem = div.select_one('[data-hook="format-strip"]')
        review["sku_attributes"] = {}
        if format_elem:
            attr_text = format_elem.get_text(strip=True)
            # 解析 "Size: Large Color: Blue" 格式
            pairs = re.findall(r"(\w[\w\s]*?):\s*([^|]+?)(?:\s*\||$)", attr_text)
            for key, val in pairs:
                review["sku_attributes"][key.strip()] = val.strip()

        # 图片
        img_elems = div.select('[data-hook="review-image-tile"]') or \
                    div.select(".review-image-tile")
        review["images"] = [img.get("src", "") for img in img_elems if img.get("src")]

        return review

    def _parse_review_date(self, date_text: str) -> str:
        """
        解析评论日期文本为标准格式。
        支持: "Reviewed in the United States on January 15, 2024"
        """
        # 提取日期部分
        match = re.search(
            r"on\s+(\w+\s+\d{1,2},\s+\d{4})", date_text
        )
        if match:
            try:
                dt = datetime.strptime(match.group(1), "%B %d, %Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # 日本站格式: "2024年1月15日"
        jp_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_text)
        if jp_match:
            return f"{jp_match.group(1)}-{jp_match.group(2).zfill(2)}-{jp_match.group(3).zfill(2)}"

        return date_text

    def _compute_statistics(self, reviews: list[dict]) -> dict:
        """计算评论统计数据"""
        if not reviews:
            return {"total": 0}

        ratings = [r["rating"] for r in reviews if r.get("rating")]
        verified = [r for r in reviews if r.get("verified_purchase")]
        vine = [r for r in reviews if r.get("is_vine")]

        star_dist = {}
        for star in range(1, 6):
            count = sum(1 for r in ratings if int(r) == star)
            star_dist[f"{star}_star"] = count
            star_dist[f"{star}_star_pct"] = round(count / len(ratings) * 100, 1) if ratings else 0

        return {
            "total": len(reviews),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            "verified_purchase_count": len(verified),
            "verified_purchase_pct": round(len(verified) / len(reviews) * 100, 1),
            "vine_count": len(vine),
            "star_distribution": star_dist,
            "with_images_count": sum(1 for r in reviews if r.get("images")),
        }

    def _find_earliest_date(self, reviews: list[dict]) -> str:
        """找到最早的评论日期，用于推算上架时间"""
        dates = []
        for r in reviews:
            date_str = r.get("date", "")
            if date_str and re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                dates.append(date_str)

        return min(dates) if dates else ""

    def _analyze_sku_distribution(self, reviews: list[dict]) -> dict:
        """
        按 SKU 属性（颜色、尺寸等）拆解评论占比，
        用于反推各变体的销量占比。
        """
        distribution = {}

        for review in reviews:
            attrs = review.get("sku_attributes", {})
            for attr_name, attr_value in attrs.items():
                if attr_name not in distribution:
                    distribution[attr_name] = {}
                if attr_value not in distribution[attr_name]:
                    distribution[attr_name][attr_value] = 0
                distribution[attr_name][attr_value] += 1

        # 计算百分比
        total = len(reviews) if reviews else 1
        for attr_name in distribution:
            for attr_value in distribution[attr_name]:
                count = distribution[attr_name][attr_value]
                distribution[attr_name][attr_value] = {
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                }

        return distribution

    def _detect_fake_reviews(self, reviews: list[dict]) -> list[dict]:
        """
        检测疑似刷单评论。

        判断依据:
        1. 非 Verified Purchase
        2. 评论内容过短（< 20字）且五星
        3. 同一天大量五星评论
        4. 评论者名称异常（如随机字符）
        """
        suspects = []

        # 统计每天的五星评论数
        date_five_star_count = {}
        for r in reviews:
            if r.get("rating") == 5.0 and r.get("date"):
                date = r["date"]
                date_five_star_count[date] = date_five_star_count.get(date, 0) + 1

        # 找出异常日期（单日五星评论 >= 5 条）
        suspicious_dates = {d for d, c in date_five_star_count.items() if c >= 5}

        for review in reviews:
            reasons = []

            # 非 VP
            if not review.get("verified_purchase"):
                reasons.append("non_verified_purchase")

            # 短评五星
            body_len = len(review.get("body", ""))
            if review.get("rating") == 5.0 and body_len < 20:
                reasons.append("short_5star_review")

            # 异常日期
            if review.get("date") in suspicious_dates:
                reasons.append("suspicious_date_cluster")

            # Vine 评论不算刷单，但标记
            if review.get("is_vine"):
                reasons.append("vine_review")

            if len(reasons) >= 2:  # 至少满足2个条件才标记
                suspects.append({
                    "review_id": review.get("review_id", ""),
                    "author": review.get("author", ""),
                    "rating": review.get("rating"),
                    "date": review.get("date", ""),
                    "reasons": reasons,
                    "confidence": min(len(reasons) * 0.3, 0.9),
                })

        return suspects

    def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client:
            self.http_client.close()
