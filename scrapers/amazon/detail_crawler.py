"""
Amazon 详情页爬虫

深度爬取商品详情页，提取完整的产品信息：
  - 基础信息（标题、品牌、价格、BSR、类目）
  - 物流信息（FBA/FBM/SFP 智能识别）
  - 全套图片（主图、SKU 变体图、A+ 详情页图片）
  - 隐藏数据（页面 JSON 中的销量预估、变体信息）
  - 产品属性（尺寸、重量、材质等）
"""

import re
import json
import time
import os
from typing import Optional

from utils.logger import get_logger
from utils.http_client import HttpClient

logger = get_logger()


class AmazonDetailCrawler:
    """
    Amazon 商品详情页爬虫

    对筛选出的核心竞品进行"解剖级"数据提取。
    """

    def __init__(self, http_client: HttpClient = None, marketplace: str = "US",
                 image_save_dir: str = "data/images"):
        self.http_client = http_client or HttpClient()
        self.marketplace = marketplace.upper()
        self.image_save_dir = image_save_dir
        os.makedirs(image_save_dir, exist_ok=True)

        domain_map = {
            "US": "www.amazon.com", "UK": "www.amazon.co.uk",
            "DE": "www.amazon.de", "JP": "www.amazon.co.jp",
            "CA": "www.amazon.ca", "AU": "www.amazon.com.au",
        }
        self.domain = domain_map.get(self.marketplace, "www.amazon.com")
        self.base_url = f"https://{self.domain}"

    def crawl_detail(self, asin: str) -> Optional[dict]:
        """
        爬取单个 ASIN 的完整详情页数据。

        :param asin: Amazon 标准识别号
        :return: 产品详情字典
        """
        url = f"{self.base_url}/dp/{asin}"
        logger.info(f"[Amazon详情] 开始爬取: {asin}")

        try:
            html = self.http_client.get(url)
            if not html:
                logger.warning(f"[Amazon详情] {asin} 页面获取失败")
                return None

            product = self._parse_detail_page(html, asin)
            if product:
                product["url"] = url
                product["marketplace"] = self.marketplace

                # 下载图片
                self._download_images(product, asin)

            return product

        except Exception as e:
            logger.error(f"[Amazon详情] {asin} 爬取异常: {e}")
            return None

    def crawl_batch(self, asins: list[str], delay: float = 2.0) -> list[dict]:
        """
        批量爬取多个 ASIN 的详情页。

        :param asins: ASIN 列表
        :param delay: 请求间隔（秒）
        :return: 产品详情列表
        """
        results = []
        total = len(asins)

        for i, asin in enumerate(asins, 1):
            logger.info(f"[Amazon详情] 进度: {i}/{total} | ASIN: {asin}")
            detail = self.crawl_detail(asin)
            if detail:
                results.append(detail)

            if i < total:
                time.sleep(delay)

        logger.info(f"[Amazon详情] 批量爬取完成: {len(results)}/{total} 成功")
        return results

    def _parse_detail_page(self, html: str, asin: str) -> Optional[dict]:
        """解析详情页 HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            product = {
                "asin": asin,
                "platform": "amazon",
                "source": "detail-crawler",
            }

            # 1. 标题
            title_elem = soup.select_one("#productTitle")
            product["title"] = title_elem.get_text(strip=True) if title_elem else ""

            # 2. 品牌
            brand_elem = soup.select_one("#bylineInfo") or soup.select_one("a#bylineInfo")
            product["brand"] = self._extract_brand(brand_elem)

            # 3. 价格
            product.update(self._extract_prices(soup))

            # 4. 星级和评论数
            product.update(self._extract_ratings(soup))

            # 5. BSR 排名
            product["bsr_ranks"] = self._extract_bsr(soup)
            product["bsr"] = product["bsr_ranks"][0]["rank"] if product["bsr_ranks"] else 0

            # 6. 类目节点
            product["category_path"] = self._extract_category_path(soup)

            # 7. 物流方式（FBA/FBM/SFP）
            product["fulfillment"] = self._detect_fulfillment(soup)

            # 8. 图片列表
            product["images"] = self._extract_all_images(soup, html)

            # 9. 变体信息
            product["variants"] = self._extract_variants(html)

            # 10. 产品属性（尺寸、重量等）
            product["attributes"] = self._extract_attributes(soup)

            # 11. A+ 内容图片
            product["aplus_images"] = self._extract_aplus_images(soup)

            # 12. 隐藏数据（从页面 JS 中提取）
            product["hidden_data"] = self._extract_hidden_data(html)

            # 13. 上架时间
            product["date_first_available"] = self._extract_first_available(soup)

            # 14. 卖家信息
            product["seller_info"] = self._extract_seller_info(soup)

            return product

        except Exception as e:
            logger.error(f"[Amazon详情] 解析失败 {asin}: {e}")
            return None

    def _extract_brand(self, elem) -> str:
        """提取品牌名"""
        if not elem:
            return ""
        text = elem.get_text(strip=True)
        # 去掉 "Visit the XXX Store" 或 "Brand: XXX" 前缀
        text = re.sub(r"^(Visit the |Brand:\s*)", "", text)
        text = re.sub(r"\s*Store$", "", text)
        return text.strip()

    def _extract_prices(self, soup) -> dict:
        """提取价格信息"""
        result = {
            "price": None,
            "list_price": None,
            "deal_price": None,
            "coupon_text": "",
        }

        # 当前售价
        price_elem = soup.select_one("#priceblock_ourprice") or \
                     soup.select_one("#priceblock_dealprice") or \
                     soup.select_one("span.a-price span.a-offscreen") or \
                     soup.select_one(".priceToPay span.a-offscreen")
        if price_elem:
            result["price"] = self._parse_price_text(price_elem.get_text())

        # 原价（划线价）
        list_price_elem = soup.select_one(".a-text-price span.a-offscreen") or \
                          soup.select_one("#listPrice")
        if list_price_elem:
            result["list_price"] = self._parse_price_text(list_price_elem.get_text())

        # 优惠券
        coupon_elem = soup.select_one("#couponBadgeRegularVpc") or \
                      soup.select_one(".couponBadge")
        if coupon_elem:
            result["coupon_text"] = coupon_elem.get_text(strip=True)

        return result

    def _parse_price_text(self, text: str) -> Optional[float]:
        """解析价格文本为浮点数"""
        if not text:
            return None
        match = re.search(r"[\d,.]+", text.replace(",", ""))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None

    def _extract_ratings(self, soup) -> dict:
        """提取评分和评论数"""
        result = {"rating": 0.0, "review_count": 0, "rating_distribution": {}}

        # 星级
        rating_elem = soup.select_one("#acrPopover") or \
                      soup.select_one('span[data-hook="rating-out-of-text"]')
        if rating_elem:
            text = rating_elem.get("title", "") or rating_elem.get_text()
            match = re.search(r"([\d.]+)", text)
            if match:
                result["rating"] = float(match.group(1))

        # 评论数
        count_elem = soup.select_one("#acrCustomerReviewCount")
        if count_elem:
            match = re.search(r"([\d,]+)", count_elem.get_text())
            if match:
                result["review_count"] = int(match.group(1).replace(",", ""))

        # 评分分布（5星、4星...各占比）
        histogram = soup.select("#histogramTable tr")
        for row in histogram:
            star_text = row.select_one(".a-text-right")
            pct_text = row.select_one(".a-text-center")
            if star_text and pct_text:
                star = star_text.get_text(strip=True).replace(" star", "")
                pct = pct_text.get_text(strip=True)
                result["rating_distribution"][star] = pct

        return result

    def _extract_bsr(self, soup) -> list[dict]:
        """提取 BSR 排名（Best Sellers Rank）"""
        bsr_list = []

        # 方法1: 产品信息表格
        detail_bullets = soup.select("#detailBulletsWrapper_feature_div li")
        for li in detail_bullets:
            text = li.get_text()
            if "Best Sellers Rank" in text or "排名" in text:
                ranks = re.findall(r"#([\d,]+)\s+in\s+(.+?)(?:\(|$)", text)
                for rank_str, category in ranks:
                    bsr_list.append({
                        "rank": int(rank_str.replace(",", "")),
                        "category": category.strip(),
                    })

        # 方法2: 产品详情表格
        if not bsr_list:
            table_rows = soup.select("#productDetails_detailBullets_sections1 tr")
            for row in table_rows:
                header = row.select_one("th")
                value = row.select_one("td")
                if header and "Best Sellers Rank" in header.get_text():
                    text = value.get_text() if value else ""
                    ranks = re.findall(r"#([\d,]+)\s+in\s+(.+?)(?:\(|$)", text)
                    for rank_str, category in ranks:
                        bsr_list.append({
                            "rank": int(rank_str.replace(",", "")),
                            "category": category.strip(),
                        })

        return bsr_list

    def _extract_category_path(self, soup) -> list[str]:
        """提取类目面包屑路径"""
        breadcrumbs = soup.select("#wayfinding-breadcrumbs_feature_div li a")
        return [a.get_text(strip=True) for a in breadcrumbs]

    def _detect_fulfillment(self, soup) -> dict:
        """
        智能识别物流方式: FBA / FBM / SFP

        - FBA (Fulfillment by Amazon): "Ships from Amazon" + "Sold by XXX"
        - FBM (Fulfillment by Merchant): "Ships from and sold by XXX"
        - SFP (Seller Fulfilled Prime): 有 Prime 标志但非 FBA
        """
        fulfillment = {
            "type": "unknown",
            "ships_from": "",
            "sold_by": "",
            "is_prime": False,
        }

        # 检查 Prime 标志
        prime_elem = soup.select_one("#prime-badge") or \
                     soup.select_one("i.a-icon-prime")
        fulfillment["is_prime"] = bool(prime_elem)

        # 提取发货方和卖家
        merchant_info = soup.select_one("#merchant-info") or \
                        soup.select_one("#tabular-buybox")

        if merchant_info:
            text = merchant_info.get_text()

            ships_match = re.search(r"Ships from\s+(.+?)(?:\.|$)", text)
            sold_match = re.search(r"Sold by\s+(.+?)(?:\.|$)", text)

            if ships_match:
                fulfillment["ships_from"] = ships_match.group(1).strip()
            if sold_match:
                fulfillment["sold_by"] = sold_match.group(1).strip()

            # 判断物流类型
            ships_from = fulfillment["ships_from"].lower()
            if "amazon" in ships_from:
                fulfillment["type"] = "FBA"
            elif fulfillment["is_prime"] and "amazon" not in ships_from:
                fulfillment["type"] = "SFP"
            else:
                fulfillment["type"] = "FBM"

        return fulfillment

    def _extract_all_images(self, soup, html: str) -> list[dict]:
        """
        提取全套图片（主图、SKU 变体图、缩略图）。
        优先从页面 JS 中的 colorImages 数据提取高清图。
        """
        images = []

        # 方法1: 从 JS 变量 colorImages 提取（高清大图）
        pattern = r"'colorImages'\s*:\s*(\{.*?\})\s*[,}]"
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                color_data = json.loads(match.group(1).replace("'", '"'))
                for variant_name, img_list in color_data.items():
                    if isinstance(img_list, list):
                        for img in img_list:
                            hi_res = img.get("hiRes") or img.get("large", "")
                            if hi_res:
                                images.append({
                                    "url": hi_res,
                                    "variant": variant_name,
                                    "type": "product",
                                })
            except (json.JSONDecodeError, AttributeError):
                pass

        # 方法2: 从缩略图列表提取
        if not images:
            thumb_elems = soup.select("#altImages li img")
            for img in thumb_elems:
                src = img.get("src", "")
                if src and "sprite" not in src:
                    # 将缩略图 URL 转换为大图 URL
                    hi_res = re.sub(r"\._[A-Z]+\d+_\.", ".", src)
                    images.append({
                        "url": hi_res,
                        "variant": "main",
                        "type": "product",
                    })

        return images

    def _extract_aplus_images(self, soup) -> list[str]:
        """提取 A+ 详情页（Enhanced Brand Content）中的图片"""
        aplus_images = []

        aplus_section = soup.select_one("#aplus") or \
                        soup.select_one("#aplusBrandStory_feature_div") or \
                        soup.select_one(".aplus-v2")

        if aplus_section:
            imgs = aplus_section.select("img")
            for img in imgs:
                src = img.get("data-src") or img.get("src", "")
                if src and "pixel" not in src and "spacer" not in src:
                    aplus_images.append(src)

        return aplus_images

    def _extract_variants(self, html: str) -> list[dict]:
        """
        提取变体信息（颜色、尺寸等）。
        从页面 JS 中的 dimensionValuesDisplayData 提取。
        """
        variants = []

        # 查找变体数据
        pattern = r"dimensionValuesDisplayData\s*:\s*(\{.*?\})\s*,"
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                for asin, dimensions in data.items():
                    variant = {"asin": asin, "dimensions": {}}
                    if isinstance(dimensions, list):
                        for i, val in enumerate(dimensions):
                            variant["dimensions"][f"dim_{i}"] = val
                    elif isinstance(dimensions, dict):
                        variant["dimensions"] = dimensions
                    variants.append(variant)
            except (json.JSONDecodeError, AttributeError):
                pass

        # 查找变体 ASIN 映射
        asin_pattern = r'"dimensionToAsinMap"\s*:\s*(\{.*?\})'
        asin_match = re.search(asin_pattern, html, re.DOTALL)
        if asin_match:
            try:
                asin_map = json.loads(asin_match.group(1))
                # 合并到 variants
                for dim_key, asin in asin_map.items():
                    existing = next((v for v in variants if v["asin"] == asin), None)
                    if not existing:
                        variants.append({
                            "asin": asin,
                            "dimensions": {"label": dim_key},
                        })
            except (json.JSONDecodeError, AttributeError):
                pass

        return variants

    def _extract_attributes(self, soup) -> dict:
        """提取产品属性（尺寸、重量、材质等）"""
        attributes = {}

        # 方法1: 详情表格
        rows = soup.select("#productDetails_techSpec_section_1 tr")
        for row in rows:
            header = row.select_one("th")
            value = row.select_one("td")
            if header and value:
                key = header.get_text(strip=True)
                val = value.get_text(strip=True)
                attributes[key] = val

        # 方法2: 详情列表
        if not attributes:
            bullets = soup.select("#detailBulletsWrapper_feature_div li")
            for li in bullets:
                text = li.get_text(strip=True)
                if ":" in text:
                    parts = text.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lstrip("\u200f\u200e")
                        val = parts[1].strip()
                        if key and val:
                            attributes[key] = val

        # 方法3: 产品信息表格
        if not attributes:
            rows = soup.select("#productDetails_detailBullets_sections1 tr")
            for row in rows:
                header = row.select_one("th")
                value = row.select_one("td")
                if header and value:
                    attributes[header.get_text(strip=True)] = value.get_text(strip=True)

        return attributes

    def _extract_hidden_data(self, html: str) -> dict:
        """
        从页面 JavaScript 中提取隐藏数据。
        包括: 销量预估参考、变体选择数据、价格区间等。
        """
        hidden = {}

        # 1. 提取 parentAsin（父 ASIN）
        parent_match = re.search(r'"parentAsin"\s*:\s*"([^"]+)"', html)
        if parent_match:
            hidden["parent_asin"] = parent_match.group(1)

        # 2. 提取 "X+ bought in past month" 销量提示
        bought_match = re.search(r"(\d+[\d,]*K?\+?)\s*bought in past month", html)
        if bought_match:
            bought_text = bought_match.group(1)
            hidden["bought_past_month"] = bought_text
            # 转换为数字
            num = bought_text.replace(",", "").replace("+", "")
            if "K" in num:
                hidden["estimated_monthly_sales"] = int(float(num.replace("K", "")) * 1000)
            else:
                try:
                    hidden["estimated_monthly_sales"] = int(num)
                except ValueError:
                    pass

        # 3. 提取 merchantId
        merchant_match = re.search(r'"merchantId"\s*:\s*"([^"]+)"', html)
        if merchant_match:
            hidden["merchant_id"] = merchant_match.group(1)

        # 4. 提取 totalOfferCount（报价数量）
        offer_match = re.search(r'"offerCount"\s*:\s*(\d+)', html)
        if offer_match:
            hidden["total_offers"] = int(offer_match.group(1))

        return hidden

    def _extract_first_available(self, soup) -> str:
        """提取首次上架日期"""
        # 在产品详情表格中查找
        selectors = [
            "#productDetails_detailBullets_sections1",
            "#detailBulletsWrapper_feature_div",
        ]
        for selector in selectors:
            section = soup.select_one(selector)
            if section:
                text = section.get_text()
                match = re.search(
                    r"Date First Available\s*[:\-]\s*(.+?)(?:\n|$)", text
                )
                if match:
                    return match.group(1).strip()
        return ""

    def _extract_seller_info(self, soup) -> dict:
        """提取卖家信息"""
        seller = {"name": "", "id": "", "rating": ""}

        seller_elem = soup.select_one("#sellerProfileTriggerId") or \
                      soup.select_one("#merchant-info a")
        if seller_elem:
            seller["name"] = seller_elem.get_text(strip=True)
            href = seller_elem.get("href", "")
            seller_id_match = re.search(r"seller=([A-Z0-9]+)", href)
            if seller_id_match:
                seller["id"] = seller_id_match.group(1)

        return seller

    def _download_images(self, product: dict, asin: str):
        """下载产品图片到本地"""
        asin_dir = os.path.join(self.image_save_dir, asin)
        os.makedirs(asin_dir, exist_ok=True)

        downloaded = []
        all_images = product.get("images", [])
        aplus = product.get("aplus_images", [])

        # 下载产品图
        for i, img in enumerate(all_images[:10]):  # 最多下载10张
            url = img.get("url", "")
            if url:
                filename = f"product_{i+1}.jpg"
                filepath = os.path.join(asin_dir, filename)
                try:
                    self.http_client.download_file(url, filepath)
                    downloaded.append(filepath)
                except Exception as e:
                    logger.debug(f"[Amazon详情] 图片下载失败: {e}")

        # 下载 A+ 图片
        for i, url in enumerate(aplus[:10]):
            filename = f"aplus_{i+1}.jpg"
            filepath = os.path.join(asin_dir, filename)
            try:
                self.http_client.download_file(url, filepath)
                downloaded.append(filepath)
            except Exception as e:
                logger.debug(f"[Amazon详情] A+图片下载失败: {e}")

        product["downloaded_images"] = downloaded
        logger.info(f"[Amazon详情] {asin} 下载了 {len(downloaded)} 张图片")

    def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client:
            self.http_client.close()
