"""
Amazon 深度数据爬取协调器

在初步筛选后，对核心竞品进行"解剖级"深度爬取：
  1. 详情页完整数据提取
  2. 评论深度挖掘
  3. 图片下载 + OCR 文字提取
  4. FBA/FBM/SFP 智能识别
  5. 变体拆解分析
  6. 卖家信息追踪
"""

import os
import time
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class AmazonDeepCrawler:
    """
    Amazon 深度爬取协调器

    整合详情页爬虫、评论爬虫、OCR 分析，
    对每个核心竞品进行全方位数据采集。
    """

    def __init__(self, http_client=None, ai_client=None,
                 marketplace: str = "US",
                 image_save_dir: str = "data/images",
                 ocr_engine: str = "gpt_vision",
                 ai_model: str = "gpt-4o"):
        """
        :param http_client: HTTP 客户端
        :param ai_client: OpenAI 客户端（用于 OCR 和 AI 分析）
        :param marketplace: 目标站点
        :param image_save_dir: 图片保存目录
        :param ocr_engine: OCR 引擎
        :param ai_model: AI 模型名称
        """
        self.marketplace = marketplace
        self.image_save_dir = image_save_dir
        self.ai_client = ai_client
        self.ai_model = ai_model

        # 延迟导入，避免循环依赖
        from scrapers.amazon.detail_crawler import AmazonDetailCrawler
        from scrapers.amazon.review_crawler import AmazonReviewCrawler
        from analysis.ai_analysis.ocr_extractor import OCRExtractor

        self.detail_crawler = AmazonDetailCrawler(
            http_client=http_client,
            marketplace=marketplace,
            image_save_dir=image_save_dir,
        )
        self.review_crawler = AmazonReviewCrawler(
            http_client=http_client,
            marketplace=marketplace,
        )
        self.ocr_extractor = OCRExtractor(
            engine=ocr_engine,
            ai_client=ai_client,
            model=ai_model,
        )

    def deep_analyze(self, asin: str, max_reviews: int = 100,
                     enable_ocr: bool = True) -> dict:
        """
        对单个 ASIN 进行深度分析。

        :param asin: Amazon ASIN
        :param max_reviews: 最大评论爬取数
        :param enable_ocr: 是否启用 OCR 分析
        :return: 完整的深度分析结果
        """
        logger.info(f"[深度爬取] 开始深度分析: {asin}")
        result = {"asin": asin, "platform": "amazon", "marketplace": self.marketplace}

        # Step 1: 详情页爬取
        logger.info(f"[深度爬取] Step 1/4: 爬取详情页")
        detail = self.detail_crawler.crawl_detail(asin)
        if detail:
            result["detail"] = detail
            result["title"] = detail.get("title", "")
            result["brand"] = detail.get("brand", "")
            result["price"] = detail.get("price")
            result["bsr"] = detail.get("bsr", 0)
            result["fulfillment"] = detail.get("fulfillment", {})
            result["variants"] = detail.get("variants", [])
            result["attributes"] = detail.get("attributes", {})
        else:
            logger.warning(f"[深度爬取] {asin} 详情页爬取失败")
            result["detail"] = None

        time.sleep(1.5)

        # Step 2: 评论深度挖掘
        logger.info(f"[深度爬取] Step 2/4: 爬取评论")
        review_data = self.review_crawler.crawl_reviews(
            asin, max_reviews=max_reviews, sort_by="recent"
        )
        result["reviews"] = review_data

        # 补充：爬取差评（1-3星）进行痛点分析
        logger.info(f"[深度爬取] 补充爬取差评")
        negative_reviews = []
        for star in [1, 2, 3]:
            neg_data = self.review_crawler.crawl_reviews(
                asin, max_reviews=20, star_filter=star, sort_by="recent"
            )
            negative_reviews.extend(neg_data.get("reviews", []))
            time.sleep(1)

        result["negative_reviews"] = negative_reviews
        result["negative_review_count"] = len(negative_reviews)

        time.sleep(1)

        # Step 3: OCR 图片文字提取
        if enable_ocr and detail:
            logger.info(f"[深度爬取] Step 3/4: OCR 图片分析")
            result["ocr_analysis"] = self._run_ocr_analysis(asin, detail)
        else:
            logger.info(f"[深度爬取] Step 3/4: 跳过 OCR 分析")
            result["ocr_analysis"] = None

        # Step 4: 综合评估
        logger.info(f"[深度爬取] Step 4/4: 综合评估")
        result["assessment"] = self._generate_assessment(result)

        logger.info(f"[深度爬取] {asin} 深度分析完成")
        return result

    def deep_analyze_batch(self, asins: list[str],
                           max_reviews: int = 100,
                           enable_ocr: bool = True,
                           delay: float = 3.0) -> list[dict]:
        """
        批量深度分析多个 ASIN。

        :param asins: ASIN 列表
        :param max_reviews: 每个 ASIN 的最大评论数
        :param enable_ocr: 是否启用 OCR
        :param delay: 请求间隔（秒）
        :return: 深度分析结果列表
        """
        results = []
        total = len(asins)

        for i, asin in enumerate(asins, 1):
            logger.info(f"[深度爬取] 批量进度: {i}/{total} | ASIN: {asin}")
            try:
                result = self.deep_analyze(asin, max_reviews, enable_ocr)
                results.append(result)
            except Exception as e:
                logger.error(f"[深度爬取] {asin} 分析失败: {e}")
                results.append({"asin": asin, "error": str(e)})

            if i < total:
                time.sleep(delay)

        logger.info(f"[深度爬取] 批量分析完成: {len(results)}/{total}")
        return results

    def _run_ocr_analysis(self, asin: str, detail: dict) -> dict:
        """对产品图片进行 OCR 分析"""
        ocr_result = {"product_images": [], "aplus_images": [], "visual_analysis": None}

        # 收集已下载的图片路径
        downloaded = detail.get("downloaded_images", [])
        asin_dir = os.path.join(self.image_save_dir, asin)

        if not downloaded and os.path.exists(asin_dir):
            downloaded = [
                os.path.join(asin_dir, f)
                for f in os.listdir(asin_dir)
                if f.endswith((".jpg", ".png", ".webp"))
            ]

        if not downloaded:
            logger.info(f"[深度爬取] {asin} 无可分析的图片")
            return ocr_result

        # 分类图片
        product_imgs = [p for p in downloaded if "product_" in os.path.basename(p)]
        aplus_imgs = [p for p in downloaded if "aplus_" in os.path.basename(p)]

        # 对产品图片进行 OCR
        if product_imgs:
            ocr_result["product_images"] = self.ocr_extractor.extract_batch(product_imgs[:5])

        # 对 A+ 图片进行 OCR
        if aplus_imgs:
            ocr_result["aplus_images"] = self.ocr_extractor.extract_batch(aplus_imgs[:5])

        # 综合视觉语义分析
        all_imgs = (product_imgs + aplus_imgs)[:8]
        if all_imgs and self.ai_client:
            ocr_result["visual_analysis"] = self.ocr_extractor.analyze_product_images(
                all_imgs, product_title=detail.get("title", "")
            )

        return ocr_result

    def _generate_assessment(self, data: dict) -> dict:
        """
        基于深度爬取的数据生成综合评估。
        """
        assessment = {
            "listing_quality": self._assess_listing_quality(data),
            "review_health": self._assess_review_health(data),
            "fulfillment_analysis": self._assess_fulfillment(data),
            "variant_analysis": self._assess_variants(data),
            "opportunity_signals": self._find_opportunities(data),
        }
        return assessment

    def _assess_listing_quality(self, data: dict) -> dict:
        """评估 Listing 质量"""
        detail = data.get("detail") or {}
        score = 0
        factors = []

        # 标题长度（80-200字符为佳）
        title = detail.get("title", "")
        if 80 <= len(title) <= 200:
            score += 20
            factors.append("标题长度合适")
        elif len(title) > 0:
            score += 10
            factors.append(f"标题长度{'过短' if len(title) < 80 else '过长'}({len(title)}字符)")

        # 图片数量（7+张为佳）
        images = detail.get("images", [])
        if len(images) >= 7:
            score += 20
            factors.append(f"图片充足({len(images)}张)")
        elif len(images) >= 4:
            score += 10
            factors.append(f"图片一般({len(images)}张)")
        else:
            factors.append(f"图片不足({len(images)}张)")

        # A+ 内容
        aplus = detail.get("aplus_images", [])
        if aplus:
            score += 20
            factors.append(f"有A+内容({len(aplus)}张)")
        else:
            factors.append("无A+内容")

        # 变体数量
        variants = detail.get("variants", [])
        if variants:
            score += 10
            factors.append(f"有变体({len(variants)}个)")

        # 品牌注册（有品牌名通常意味着已注册）
        brand = detail.get("brand", "")
        if brand:
            score += 10
            factors.append(f"有品牌({brand})")

        # OCR 分析结果
        ocr = data.get("ocr_analysis") or {}
        visual = ocr.get("visual_analysis") or {}
        if visual.get("overall", {}).get("aplus_quality", 0) >= 7:
            score += 20
            factors.append("视觉内容质量高")
        elif visual:
            score += 10

        return {
            "score": min(score, 100),
            "grade": self._score_to_grade(score),
            "factors": factors,
        }

    def _assess_review_health(self, data: dict) -> dict:
        """评估评论健康度"""
        review_data = data.get("reviews", {})
        stats = review_data.get("statistics", {})
        suspects = review_data.get("fake_review_suspects", [])

        score = 100
        factors = []

        # 评分
        avg_rating = stats.get("average_rating", 0)
        if avg_rating >= 4.5:
            factors.append(f"评分优秀({avg_rating})")
        elif avg_rating >= 4.0:
            score -= 10
            factors.append(f"评分良好({avg_rating})")
        elif avg_rating >= 3.5:
            score -= 25
            factors.append(f"评分一般({avg_rating})")
        else:
            score -= 40
            factors.append(f"评分较差({avg_rating})")

        # VP 比例
        vp_pct = stats.get("verified_purchase_pct", 0)
        if vp_pct < 70:
            score -= 20
            factors.append(f"VP比例偏低({vp_pct}%)")
        else:
            factors.append(f"VP比例正常({vp_pct}%)")

        # 刷单嫌疑
        if suspects:
            suspect_pct = len(suspects) / max(stats.get("total", 1), 1) * 100
            if suspect_pct > 20:
                score -= 30
                factors.append(f"刷单嫌疑高({len(suspects)}条, {suspect_pct:.1f}%)")
            elif suspect_pct > 10:
                score -= 15
                factors.append(f"有刷单嫌疑({len(suspects)}条, {suspect_pct:.1f}%)")

        # Vine 评论占比
        vine_count = stats.get("vine_count", 0)
        if vine_count > 0:
            factors.append(f"有Vine评论({vine_count}条)")

        return {
            "score": max(score, 0),
            "grade": self._score_to_grade(max(score, 0)),
            "factors": factors,
        }

    def _assess_fulfillment(self, data: dict) -> dict:
        """评估物流方式"""
        fulfillment = data.get("fulfillment", {})
        f_type = fulfillment.get("type", "unknown") if isinstance(fulfillment, dict) else str(fulfillment)

        analysis = {
            "type": f_type,
            "is_prime": fulfillment.get("is_prime", False) if isinstance(fulfillment, dict) else False,
            "ships_from": fulfillment.get("ships_from", "") if isinstance(fulfillment, dict) else "",
            "sold_by": fulfillment.get("sold_by", "") if isinstance(fulfillment, dict) else "",
        }

        if f_type == "FBA":
            analysis["advantage"] = "FBA发货，享受Prime配送，Buy Box竞争力强"
            analysis["implication"] = "竞品使用FBA，新卖家也建议FBA以保持竞争力"
        elif f_type == "FBM":
            analysis["advantage"] = "FBM发货，利润率可能更高"
            analysis["implication"] = "竞品使用FBM，FBA入场可能获得配送优势"
        elif f_type == "SFP":
            analysis["advantage"] = "SFP发货，自发货但享有Prime标志"
            analysis["implication"] = "竞品使用SFP，说明有较强的物流能力"

        return analysis

    def _assess_variants(self, data: dict) -> dict:
        """评估变体策略"""
        detail = data.get("detail") or {}
        variants = detail.get("variants", [])
        review_data = data.get("reviews", {})
        sku_dist = review_data.get("sku_distribution", {})

        analysis = {
            "variant_count": len(variants),
            "sku_distribution": sku_dist,
        }

        if variants:
            analysis["strategy"] = "多变体策略，通过颜色/尺寸等变体聚合评论和流量"
            analysis["recommendation"] = "建议也采用变体策略，利用评论聚合效应"

            # 找出最热门的变体
            if sku_dist:
                for attr_name, attr_values in sku_dist.items():
                    if isinstance(attr_values, dict):
                        sorted_vals = sorted(
                            attr_values.items(),
                            key=lambda x: x[1].get("count", 0) if isinstance(x[1], dict) else 0,
                            reverse=True
                        )
                        if sorted_vals:
                            top_val = sorted_vals[0]
                            analysis[f"top_{attr_name}"] = top_val[0]
        else:
            analysis["strategy"] = "单品策略，无变体"
            analysis["recommendation"] = "可考虑增加变体以扩大覆盖面"

        return analysis

    def _find_opportunities(self, data: dict) -> list[str]:
        """发现市场机会信号"""
        opportunities = []

        detail = data.get("detail") or {}
        review_data = data.get("reviews", {})
        stats = review_data.get("statistics", {})
        negative = data.get("negative_reviews", [])

        # 1. 评分低于4.0 = 产品有改进空间
        avg_rating = stats.get("average_rating", 0)
        if 0 < avg_rating < 4.0:
            opportunities.append(f"竞品评分仅{avg_rating}，存在产品改进机会")

        # 2. 差评多 = 痛点明确
        if len(negative) >= 10:
            opportunities.append(f"竞品有{len(negative)}条差评，可深入分析用户痛点")

        # 3. 无A+内容 = Listing优化空间
        if not detail.get("aplus_images"):
            opportunities.append("竞品无A+内容，优质Listing可获得视觉优势")

        # 4. 图片少 = 展示不充分
        images = detail.get("images", [])
        if len(images) < 5:
            opportunities.append(f"竞品仅{len(images)}张图片，充分展示可获得优势")

        # 5. FBM发货 = FBA可获得配送优势
        fulfillment = data.get("fulfillment", {})
        if isinstance(fulfillment, dict) and fulfillment.get("type") == "FBM":
            opportunities.append("竞品使用FBM，FBA入场可获得Prime标志和配送优势")

        # 6. 无变体 = 可通过变体策略扩大覆盖
        if not detail.get("variants"):
            opportunities.append("竞品无变体，多变体策略可聚合流量")

        return opportunities

    @staticmethod
    def _score_to_grade(score: int) -> str:
        """分数转等级"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def close(self):
        """关闭资源"""
        if hasattr(self, 'detail_crawler'):
            self.detail_crawler.close()
        if hasattr(self, 'review_crawler'):
            self.review_crawler.close()
