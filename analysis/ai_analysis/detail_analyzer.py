"""
Coupang 选品系统 - AI 详情页分析模块
功能:
  1. 逻辑结构分析（痛点引入/原理拆解/竞品对比/信任背书/限时促销）
  2. 文本语义分析（OCR提取文案 → 关键词频次/语气/USP）
  3. 信任锚点分析（认证图标/检测报告/明星背书/真实场景）
  4. 视觉语义分析（配色/排版/风格）
"""

import os
import json
import base64
from typing import Optional

from utils.logger import get_logger
from i18n import t, get_language

logger = get_logger()


class DetailPageAnalyzer:
    """
    AI 详情页分析器
    结合 GPT-4 Vision 和 OCR 对详情页进行多维度分析
    """

    def __init__(self, ai_client=None):
        """
        :param ai_client: OpenAI 客户端实例
        """
        self.ai_client = ai_client

    def analyze(self, product_data: dict, detail_images: list[str] = None) -> dict:
        """
        对产品详情页进行全面分析

        :param product_data: 产品基础数据（标题、价格、规格等）
        :param detail_images: 详情页图片本地路径列表
        :return: 分析结果
        """
        logger.info(t("analysis.detail_analysis_start"))

        result = {
            "delivery_analysis": self._analyze_delivery(product_data),
            "logic_structure": {},
            "text_semantics": {},
            "trust_signals": {},
            "visual_semantics": {},
            "competitive_dimensions": [],
        }

        if self.ai_client and detail_images:
            # 使用AI Vision分析详情页图片
            ai_result = self._ai_vision_analysis(product_data, detail_images)
            result.update(ai_result)
        elif self.ai_client:
            # 仅基于文本数据分析
            ai_result = self._ai_text_analysis(product_data)
            result.update(ai_result)

        logger.info(t("analysis.analysis_complete"))
        return result

    def _analyze_delivery(self, product_data: dict) -> dict:
        """分析配送方式及其含义"""
        delivery_type = product_data.get("delivery_type", "unknown")

        delivery_info = {
            "blue_rocket": {
                "type": "blue_rocket",
                "name_zh": "蓝火箭（Coupang自营仓）",
                "name_en": "Blue Rocket (Coupang Fulfillment)",
                "name_ko": "로켓배송",
                "description": "Coupang自营仓储配送，次日达，消费者信任度最高",
                "seller_implication": "需要将货物提前入库到Coupang仓库，库存管理要求高",
                "competitiveness": "high",
            },
            "orange_rocket": {
                "type": "orange_rocket",
                "name_zh": "橙火箭（卖家发货-Coupang配送）",
                "name_en": "Orange Rocket (Seller Ships - Coupang Delivers)",
                "name_ko": "로켓그로스",
                "description": "卖家发货到Coupang配送中心，由Coupang完成最后一公里配送",
                "seller_implication": "适合跨境卖家，需要对接Coupang物流体系",
                "competitiveness": "medium-high",
            },
            "purple_rocket": {
                "type": "purple_rocket",
                "name_zh": "紫火箭（跨境直邮）",
                "name_en": "Purple Rocket (Cross-border Direct Mail)",
                "name_ko": "로켓직구",
                "description": "海外仓直邮到韩国，配送时间较长但适合跨境卖家",
                "seller_implication": "跨境卖家最常用方式，无需韩国本地仓储",
                "competitiveness": "medium",
            },
            "self_delivery": {
                "type": "self_delivery",
                "name_zh": "自发货",
                "name_en": "Self Delivery",
                "name_ko": "판매자배송",
                "description": "卖家自行安排配送，灵活性高但消费者信任度较低",
                "seller_implication": "需要自行解决物流，适合有韩国本地仓的卖家",
                "competitiveness": "low",
            },
        }

        return delivery_info.get(delivery_type, {
            "type": "unknown",
            "name_zh": "未知",
            "name_en": "Unknown",
            "name_ko": "알 수 없음",
            "description": "无法识别配送方式",
            "competitiveness": "unknown",
        })

    def _ai_vision_analysis(self, product_data: dict, image_paths: list[str]) -> dict:
        """
        使用 GPT-4 Vision 分析详情页图片

        :param product_data: 产品数据
        :param image_paths: 图片本地路径列表（最多取前10张）
        """
        logger.info(t("analysis.ai_analyzing"))

        # 准备图片（Base64编码，最多10张）
        images_content = []
        for path in image_paths[:10]:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode("utf-8")
                    ext = os.path.splitext(path)[1].lower()
                    mime = {"jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
                    images_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{img_data}"}
                    })
                except Exception as e:
                    logger.debug(f"Failed to encode image {path}: {e}")

        if not images_content:
            return self._ai_text_analysis(product_data)

        lang = get_language()
        output_lang = {"zh_CN": "Chinese", "en_US": "English", "ko_KR": "Korean"}.get(lang, "Chinese")

        prompt = f"""You are an expert e-commerce product listing analyst for Coupang.

Product: {product_data.get('title', '')}
Price: {product_data.get('price', 'N/A')} KRW

Analyze the product detail page images and provide a structured JSON response:

1. "logic_structure": Analyze the page's persuasion logic flow:
   - "flow_steps": ordered list of content blocks (e.g., pain point intro → solution → features → social proof → CTA)
   - "conversion_model": identified model (AIDA/PAS/FAB/other)
   - "effectiveness_score": 1-10 rating

2. "text_semantics": Analyze text/copy in the images:
   - "key_claims": main product claims
   - "keyword_frequency": important keywords and their emphasis level
   - "tone": overall tone (emotional/rational/technical/lifestyle)
   - "usp_points": unique selling propositions

3. "trust_signals": Identify trust-building elements:
   - "certifications": any certification badges/logos
   - "test_reports": lab test results or quality reports
   - "endorsements": celebrity/expert endorsements
   - "real_scenes": real-life usage photos
   - "social_proof": review counts, sales numbers shown
   - "trust_score": 1-10 overall trust level

4. "visual_semantics": Analyze visual design:
   - "color_scheme": primary colors and their psychological effect
   - "layout_style": layout pattern (grid/scroll/comparison)
   - "image_quality": 1-10 quality rating
   - "design_style": overall style (premium/budget/minimalist/busy)
   - "target_audience_fit": how well design matches target audience

5. "competitive_dimensions": List 3-5 key dimensions this product competes on (e.g., battery life, size, color options)

Respond in {output_lang}. Return ONLY valid JSON."""

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        *images_content,
                    ]
                }
            ]

            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=3000,
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            return json.loads(result_text)

        except Exception as e:
            logger.error(f"AI Vision analysis error: {e}")
            return self._ai_text_analysis(product_data)

    def _ai_text_analysis(self, product_data: dict) -> dict:
        """
        仅基于文本数据的AI分析（无图片时的降级方案）
        """
        if not self.ai_client:
            return {}

        lang = get_language()
        output_lang = {"zh_CN": "Chinese", "en_US": "English", "ko_KR": "Korean"}.get(lang, "Chinese")

        specs = product_data.get("specifications", {})
        specs_text = "\n".join([f"- {k}: {v}" for k, v in specs.items()]) if specs else "N/A"

        prompt = f"""Analyze this Coupang product listing and provide insights.

Product: {product_data.get('title', '')}
Brand: {product_data.get('brand_name', 'N/A')}
Price: {product_data.get('price', 'N/A')} KRW
Rating: {product_data.get('rating', 'N/A')}
Reviews: {product_data.get('review_count', 0)}
Delivery: {product_data.get('delivery_type', 'unknown')}
Specifications:
{specs_text}

Provide a JSON response with:
1. "competitive_dimensions": 3-5 key competition dimensions for this product type
2. "text_semantics": {{"key_claims": [...], "usp_points": [...], "tone": "..."}}
3. "market_positioning": brief market positioning analysis

Respond in {output_lang}. Return ONLY valid JSON."""

        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            return json.loads(result_text)

        except Exception as e:
            logger.error(f"AI text analysis error: {e}")
            return {}
