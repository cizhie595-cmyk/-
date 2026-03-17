"""
OCR 图片文字提取模块

对商品详情页图片（主图、A+ 图片）进行 OCR 识别，
提取图片中的卖点文案、参数信息、品牌标识等。

支持多种 OCR 引擎：
  - Tesseract（本地免费）
  - GPT-4 Vision（多模态 AI，精度最高）
  - 百度/腾讯 OCR API（中文识别优化）
"""

import os
import re
import base64
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class OCRExtractor:
    """
    图片文字提取器

    从商品图片中提取文案信息，辅助 AI 分析模块
    理解竞品的视觉营销策略。
    """

    # 支持的 OCR 引擎
    ENGINE_TESSERACT = "tesseract"
    ENGINE_GPT_VISION = "gpt_vision"
    ENGINE_CLOUD_API = "cloud_api"

    def __init__(self, engine: str = "gpt_vision", ai_client=None,
                 model: str = "gpt-4o", language: str = "eng"):
        """
        :param engine: OCR 引擎 (tesseract / gpt_vision / cloud_api)
        :param ai_client: OpenAI 客户端（用于 GPT Vision）
        :param model: GPT 模型名称
        :param language: Tesseract 语言代码
        """
        self.engine = engine
        self.ai_client = ai_client
        self.model = model
        self.language = language

    def extract_text(self, image_path: str) -> dict:
        """
        从单张图片中提取文字。

        :param image_path: 图片文件路径
        :return: {"raw_text": str, "structured": dict, "confidence": float}
        """
        if not os.path.exists(image_path):
            logger.error(f"[OCR] 图片不存在: {image_path}")
            return {"raw_text": "", "structured": {}, "confidence": 0}

        logger.info(f"[OCR] 提取文字: {image_path} | 引擎: {self.engine}")

        if self.engine == self.ENGINE_GPT_VISION:
            return self._extract_with_gpt_vision(image_path)
        elif self.engine == self.ENGINE_TESSERACT:
            return self._extract_with_tesseract(image_path)
        elif self.engine == self.ENGINE_CLOUD_API:
            return self._extract_with_cloud_api(image_path)
        else:
            logger.error(f"[OCR] 不支持的引擎: {self.engine}")
            return {"raw_text": "", "structured": {}, "confidence": 0}

    def extract_batch(self, image_paths: list[str]) -> list[dict]:
        """批量提取多张图片的文字"""
        results = []
        for path in image_paths:
            result = self.extract_text(path)
            result["image_path"] = path
            results.append(result)
        return results

    def analyze_product_images(self, image_paths: list[str],
                               product_title: str = "") -> dict:
        """
        对一组商品图片进行综合视觉语义分析。

        不仅提取文字，还分析：
          - 图片质量评估
          - 卖点文案提取
          - 品牌元素识别
          - 场景/生活方式展示
          - A+ 内容质量评估
        """
        if not self.ai_client:
            logger.warning("[OCR] AI 客户端未配置，无法进行视觉语义分析")
            return {}

        logger.info(f"[OCR] 开始视觉语义分析 | 图片数: {len(image_paths)}")

        # 编码图片（最多分析 8 张）
        image_contents = []
        for path in image_paths[:8]:
            encoded = self._encode_image(path)
            if encoded:
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded}",
                        "detail": "high",
                    }
                })

        if not image_contents:
            return {}

        prompt_text = f"""You are an Amazon product listing analyst. Analyze these product images comprehensively.

Product title: "{product_title}"

For each image, extract and analyze:
1. **OCR Text**: All visible text in the image (selling points, specs, brand name)
2. **Image Type**: main_photo / lifestyle / infographic / comparison / aplus / size_chart / packaging
3. **Quality Score**: 1-10 (lighting, resolution, professionalism)
4. **Selling Points**: Key marketing messages visible
5. **Brand Elements**: Logo, brand colors, brand name placement

Then provide an overall assessment:
- **Visual Strategy**: What visual marketing strategy is the seller using?
- **Strengths**: What the listing does well visually
- **Weaknesses**: What could be improved
- **A+ Content Quality**: Rate the enhanced content quality (if present)

Return as JSON:
{{
  "images": [
    {{
      "index": 1,
      "type": "main_photo",
      "ocr_text": "extracted text...",
      "quality_score": 8,
      "selling_points": ["point1", "point2"],
      "brand_elements": ["logo visible", "brand color blue"]
    }}
  ],
  "overall": {{
    "visual_strategy": "...",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "aplus_quality": 7,
    "total_selling_points": ["..."],
    "brand_consistency": 8
  }}
}}"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    *image_contents,
                ]
            }
        ]

        try:
            response = self.ai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=3000,
            )
            result_text = response.choices[0].message.content.strip()

            # 解析 JSON
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            import json
            return json.loads(result_text)

        except Exception as e:
            logger.error(f"[OCR] 视觉语义分析失败: {e}")
            return {}

    # ================================================================
    # GPT Vision 引擎
    # ================================================================

    def _extract_with_gpt_vision(self, image_path: str) -> dict:
        """使用 GPT-4 Vision 提取图片文字"""
        if not self.ai_client:
            logger.error("[OCR] GPT Vision 需要 AI 客户端")
            return {"raw_text": "", "structured": {}, "confidence": 0}

        encoded = self._encode_image(image_path)
        if not encoded:
            return {"raw_text": "", "structured": {}, "confidence": 0}

        try:
            response = self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Extract ALL text visible in this product image. 
Return as JSON:
{
  "raw_text": "all text as a single string",
  "structured": {
    "brand_name": "brand if visible",
    "product_name": "product name if visible",
    "selling_points": ["point1", "point2"],
    "specifications": {"key": "value"},
    "certifications": ["cert1"],
    "price_text": "price if visible",
    "other_text": ["any other text"]
  },
  "confidence": 0.95
}
Only return the JSON, no other text."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded}",
                                    "detail": "high",
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=1500,
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            import json
            return json.loads(result_text)

        except Exception as e:
            logger.error(f"[OCR] GPT Vision 提取失败: {e}")
            return {"raw_text": "", "structured": {}, "confidence": 0}

    # ================================================================
    # Tesseract 引擎（本地免费）
    # ================================================================

    def _extract_with_tesseract(self, image_path: str) -> dict:
        """使用 Tesseract OCR 提取文字"""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(image_path)

            # 预处理：灰度化、增强对比度
            img = img.convert("L")

            # OCR 识别
            text = pytesseract.image_to_string(img, lang=self.language)
            data = pytesseract.image_to_data(img, lang=self.language, output_type=pytesseract.Output.DICT)

            # 计算平均置信度
            confidences = [int(c) for c in data["conf"] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0

            # 结构化提取
            structured = self._structure_ocr_text(text)

            return {
                "raw_text": text.strip(),
                "structured": structured,
                "confidence": round(avg_confidence, 2),
            }

        except ImportError:
            logger.error("[OCR] Tesseract 未安装，请运行: sudo apt install tesseract-ocr && pip install pytesseract")
            return {"raw_text": "", "structured": {}, "confidence": 0}
        except Exception as e:
            logger.error(f"[OCR] Tesseract 提取失败: {e}")
            return {"raw_text": "", "structured": {}, "confidence": 0}

    # ================================================================
    # 云端 OCR API
    # ================================================================

    def _extract_with_cloud_api(self, image_path: str) -> dict:
        """
        使用云端 OCR API 提取文字。
        预留接口，支持接入百度/腾讯/Google Cloud Vision。
        """
        logger.warning("[OCR] 云端 OCR API 尚未配置，请在设置中配置 API Key")
        return {"raw_text": "", "structured": {}, "confidence": 0}

    # ================================================================
    # 工具方法
    # ================================================================

    @staticmethod
    def _encode_image(image_path: str) -> Optional[str]:
        """将图片编码为 Base64"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"[OCR] 图片编码失败: {e}")
            return None

    @staticmethod
    def _structure_ocr_text(raw_text: str) -> dict:
        """对 Tesseract 的原始文本进行结构化解析"""
        structured = {
            "selling_points": [],
            "specifications": {},
            "other_text": [],
        }

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        for line in lines:
            # 识别规格参数（包含冒号或等号的行）
            if ":" in line or "=" in line:
                parts = re.split(r"[:=]", line, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val:
                        structured["specifications"][key] = val
                        continue

            # 识别卖点（以 ✓ ★ • - 等开头的行）
            if re.match(r"^[✓★•\-\+►▸]", line):
                structured["selling_points"].append(line.lstrip("✓★•-+►▸ "))
                continue

            # 其他文本
            if len(line) > 3:
                structured["other_text"].append(line)

        return structured
