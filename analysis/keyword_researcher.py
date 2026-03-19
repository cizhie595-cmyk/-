"""
关键词研究工具 (Keyword Researcher)

Step 3 扩展模块 - 搜索量估算、关键词建议、长尾词挖掘、关键词难度评估

功能:
1. 从 Amazon 自动补全 API 获取关键词建议
2. 基于产品数据估算搜索量（通过 BSR 和评论数反推）
3. 长尾关键词挖掘（组合变体、问题词、属性词）
4. 关键词竞争难度评估
5. 关键词分组和优先级排序
"""

import re
import json
from datetime import datetime
from typing import Optional
from collections import Counter

from utils.logger import get_logger

logger = get_logger()


class KeywordResearcher:
    """
    Amazon 关键词研究工具

    通过 Amazon Autocomplete、产品数据分析和 AI 辅助，
    提供全面的关键词研究和优化建议。
    """

    # Amazon Autocomplete API 端点
    AUTOCOMPLETE_URLS = {
        "US": "https://completion.amazon.com/api/2017/suggestions?mid=ATVPDKIKX0DER&alias=aps&prefix=",
        "UK": "https://completion.amazon.co.uk/api/2017/suggestions?mid=A1F83G8C2ARO7P&alias=aps&prefix=",
        "DE": "https://completion.amazon.de/api/2017/suggestions?mid=A1PA6795UKMFR9&alias=aps&prefix=",
        "JP": "https://completion.amazon.co.jp/api/2017/suggestions?mid=A1VC38T7YXB528&alias=aps&prefix=",
    }

    # 长尾词修饰语
    MODIFIERS = {
        "intent": ["best", "top", "cheap", "premium", "professional", "portable",
                    "small", "large", "mini", "wireless", "waterproof", "organic"],
        "question": ["how to", "what is", "which", "where to buy", "is it worth"],
        "comparison": ["vs", "versus", "or", "compared to", "alternative to"],
        "buying": ["buy", "deal", "discount", "coupon", "sale", "review",
                   "price", "cost", "worth it"],
        "attribute": ["for men", "for women", "for kids", "for beginners",
                      "for home", "for office", "for travel", "for outdoor"],
    }

    def __init__(self, http_client=None, ai_client=None, marketplace: str = "US"):
        """
        :param http_client: HTTP 客户端
        :param ai_client: OpenAI 客户端（用于 AI 辅助分析）
        :param marketplace: 市场站点
        """
        self.http_client = http_client
        self.ai_client = ai_client
        self.marketplace = marketplace

    # ================================================================
    # Amazon 自动补全关键词
    # ================================================================

    def get_autocomplete_suggestions(self, seed_keyword: str,
                                      max_depth: int = 2) -> list[dict]:
        """
        从 Amazon Autocomplete API 获取关键词建议

        :param seed_keyword: 种子关键词
        :param max_depth: 递归深度（1=只查种子词，2=对结果再查一次）
        :return: 关键词建议列表
        """
        suggestions = []
        seen = set()

        # 第一层：直接查询种子词
        first_level = self._fetch_autocomplete(seed_keyword)
        for kw in first_level:
            if kw not in seen:
                seen.add(kw)
                suggestions.append({
                    "keyword": kw,
                    "source": "autocomplete",
                    "depth": 1,
                    "seed": seed_keyword,
                })

        # 第二层：对每个结果再查询（限制数量避免过多请求）
        if max_depth >= 2:
            for item in suggestions[:10]:
                second_level = self._fetch_autocomplete(item["keyword"])
                for kw in second_level:
                    if kw not in seen:
                        seen.add(kw)
                        suggestions.append({
                            "keyword": kw,
                            "source": "autocomplete",
                            "depth": 2,
                            "seed": item["keyword"],
                        })

        # 字母扩展：seed + a, seed + b, ..., seed + z
        for letter in "abcdefghijklmnopqrstuvwxyz":
            expanded = self._fetch_autocomplete(f"{seed_keyword} {letter}")
            for kw in expanded:
                if kw not in seen:
                    seen.add(kw)
                    suggestions.append({
                        "keyword": kw,
                        "source": "alpha_expand",
                        "depth": 1,
                        "seed": f"{seed_keyword} {letter}",
                    })

        logger.info(f"自动补全建议: {len(suggestions)} 个关键词 (种子: {seed_keyword})")
        return suggestions

    def _fetch_autocomplete(self, prefix: str) -> list[str]:
        """调用 Amazon Autocomplete API"""
        base_url = self.AUTOCOMPLETE_URLS.get(self.marketplace, self.AUTOCOMPLETE_URLS["US"])
        url = base_url + prefix.replace(" ", "+")

        try:
            if self.http_client:
                resp = self.http_client.get(url, headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                })
            else:
                import requests
                resp = requests.get(url, headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                }, timeout=10)

            if hasattr(resp, "json"):
                data = resp.json() if callable(resp.json) else resp.json
            elif hasattr(resp, "text"):
                data = json.loads(resp.text)
            else:
                return []

            suggestions = data.get("suggestions", [])
            return [s.get("value", "") for s in suggestions if s.get("value")]
        except Exception as e:
            logger.debug(f"Autocomplete 请求失败: {e}")
            return []

    # ================================================================
    # 长尾关键词挖掘
    # ================================================================

    def generate_long_tail_keywords(self, seed_keyword: str) -> list[dict]:
        """
        生成长尾关键词变体

        通过组合修饰语、问题词、属性词等生成长尾关键词。

        :param seed_keyword: 种子关键词
        :return: 长尾关键词列表
        """
        long_tails = []
        seen = set()

        for category, modifiers in self.MODIFIERS.items():
            for mod in modifiers:
                # 前置修饰: "best {keyword}"
                kw_front = f"{mod} {seed_keyword}"
                if kw_front not in seen:
                    seen.add(kw_front)
                    long_tails.append({
                        "keyword": kw_front,
                        "source": "modifier",
                        "category": category,
                        "modifier": mod,
                        "position": "prefix",
                    })

                # 后置修饰: "{keyword} for men"
                kw_back = f"{seed_keyword} {mod}"
                if kw_back not in seen:
                    seen.add(kw_back)
                    long_tails.append({
                        "keyword": kw_back,
                        "source": "modifier",
                        "category": category,
                        "modifier": mod,
                        "position": "suffix",
                    })

        logger.info(f"长尾关键词生成: {len(long_tails)} 个 (种子: {seed_keyword})")
        return long_tails

    # ================================================================
    # 搜索量估算
    # ================================================================

    def estimate_search_volume(self, keyword: str,
                                products: list[dict] = None) -> dict:
        """
        基于产品数据估算关键词搜索量

        使用 BSR 排名和评论数反推月搜索量的经验公式:
        - 月搜索量 ≈ 首页产品平均月销量 × 首页产品数 / CTR
        - 月销量 ≈ 评论数 × 评论转化率系数

        :param keyword: 关键词
        :param products: 搜索该关键词返回的产品列表
        :return: 搜索量估算结果
        """
        result = {
            "keyword": keyword,
            "estimated_monthly_searches": 0,
            "confidence": "low",
            "method": "product_data_inference",
            "details": {},
        }

        if not products:
            return result

        # 提取首页产品的关键指标
        review_counts = []
        prices = []
        ratings = []
        bsr_ranks = []

        for p in products[:20]:  # 只看前 20 个（首页）
            rc = p.get("review_count") or p.get("reviews") or 0
            if rc:
                review_counts.append(int(rc))
            price = p.get("price") or p.get("price_current") or 0
            if price:
                prices.append(float(price))
            rating = p.get("rating") or 0
            if rating:
                ratings.append(float(rating))
            bsr = p.get("bsr_rank") or p.get("bsr") or 0
            if bsr:
                bsr_ranks.append(int(bsr))

        if not review_counts:
            return result

        # 经验公式估算
        avg_reviews = sum(review_counts) / len(review_counts)
        review_to_sale_ratio = 0.05  # 约 5% 的购买者会留评
        avg_monthly_sales = avg_reviews * review_to_sale_ratio * 30 / 365  # 假设评论累积 1 年
        ctr_first_page = 0.35  # 首页点击率约 35%
        conversion_rate = 0.12  # Amazon 平均转化率约 12%

        # 月搜索量 = 首页总销量 / (CTR × 转化率)
        first_page_total_sales = avg_monthly_sales * min(len(review_counts), 20)
        estimated_searches = first_page_total_sales / (ctr_first_page * conversion_rate)

        # 根据数据量调整置信度
        if len(review_counts) >= 15:
            confidence = "high"
        elif len(review_counts) >= 8:
            confidence = "medium"
        else:
            confidence = "low"

        result.update({
            "estimated_monthly_searches": int(estimated_searches),
            "confidence": confidence,
            "details": {
                "avg_reviews": round(avg_reviews, 1),
                "avg_price": round(sum(prices) / len(prices), 2) if prices else 0,
                "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                "avg_bsr": int(sum(bsr_ranks) / len(bsr_ranks)) if bsr_ranks else 0,
                "products_analyzed": len(review_counts),
                "estimated_avg_monthly_sales": int(avg_monthly_sales),
            },
        })

        return result

    # ================================================================
    # 关键词竞争难度评估
    # ================================================================

    def assess_keyword_difficulty(self, keyword: str,
                                   products: list[dict] = None) -> dict:
        """
        评估关键词竞争难度

        基于首页产品的评论数、评分、品牌集中度等指标计算难度分数。

        :param keyword: 关键词
        :param products: 搜索结果产品列表
        :return: 难度评估结果 (0-100 分)
        """
        result = {
            "keyword": keyword,
            "difficulty_score": 50,  # 默认中等
            "difficulty_level": "Medium",
            "factors": {},
            "recommendation": "",
        }

        if not products:
            return result

        top_products = products[:20]
        factors = {}

        # 因素 1: 平均评论数（评论越多越难）
        review_counts = [
            int(p.get("review_count") or p.get("reviews") or 0)
            for p in top_products
        ]
        avg_reviews = sum(review_counts) / len(review_counts) if review_counts else 0
        if avg_reviews > 5000:
            factors["review_barrier"] = {"score": 90, "detail": f"平均评论 {avg_reviews:.0f}，极高壁垒"}
        elif avg_reviews > 1000:
            factors["review_barrier"] = {"score": 70, "detail": f"平均评论 {avg_reviews:.0f}，高壁垒"}
        elif avg_reviews > 300:
            factors["review_barrier"] = {"score": 50, "detail": f"平均评论 {avg_reviews:.0f}，中等壁垒"}
        elif avg_reviews > 50:
            factors["review_barrier"] = {"score": 30, "detail": f"平均评论 {avg_reviews:.0f}，较低壁垒"}
        else:
            factors["review_barrier"] = {"score": 10, "detail": f"平均评论 {avg_reviews:.0f}，低壁垒"}

        # 因素 2: 平均评分（评分高说明产品成熟）
        ratings = [
            float(p.get("rating") or 0)
            for p in top_products if p.get("rating")
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        if avg_rating >= 4.5:
            factors["quality_bar"] = {"score": 80, "detail": f"平均评分 {avg_rating:.1f}，质量要求高"}
        elif avg_rating >= 4.0:
            factors["quality_bar"] = {"score": 50, "detail": f"平均评分 {avg_rating:.1f}，质量要求中等"}
        else:
            factors["quality_bar"] = {"score": 20, "detail": f"平均评分 {avg_rating:.1f}，存在改进空间"}

        # 因素 3: 品牌集中度（品牌越集中越难入场）
        brands = [
            p.get("brand", "unknown").lower()
            for p in top_products if p.get("brand")
        ]
        brand_counter = Counter(brands)
        top_brand_share = 0
        if brand_counter:
            top_brand_count = brand_counter.most_common(1)[0][1]
            top_brand_share = top_brand_count / len(brands) * 100 if brands else 0

        if top_brand_share > 50:
            factors["brand_monopoly"] = {"score": 90, "detail": f"头部品牌占比 {top_brand_share:.0f}%，高度垄断"}
        elif top_brand_share > 30:
            factors["brand_monopoly"] = {"score": 60, "detail": f"头部品牌占比 {top_brand_share:.0f}%，中度集中"}
        else:
            factors["brand_monopoly"] = {"score": 25, "detail": f"头部品牌占比 {top_brand_share:.0f}%，竞争分散"}

        # 因素 4: 价格竞争（价格区间窄说明价格战激烈）
        prices = [
            float(p.get("price") or p.get("price_current") or 0)
            for p in top_products if p.get("price") or p.get("price_current")
        ]
        if prices:
            price_range = max(prices) - min(prices)
            avg_price = sum(prices) / len(prices)
            price_spread = price_range / avg_price * 100 if avg_price > 0 else 0

            if price_spread < 20:
                factors["price_competition"] = {"score": 80, "detail": f"价格区间窄 ({price_spread:.0f}%)，价格战激烈"}
            elif price_spread < 50:
                factors["price_competition"] = {"score": 50, "detail": f"价格区间中等 ({price_spread:.0f}%)"}
            else:
                factors["price_competition"] = {"score": 20, "detail": f"价格区间宽 ({price_spread:.0f}%)，有定价空间"}

        # 因素 5: FBA 占比（FBA 占比高说明专业卖家多）
        fba_count = sum(
            1 for p in top_products
            if (p.get("fulfillment_type") or p.get("fulfillment") or "").upper() in ("FBA", "AMAZON")
        )
        fba_ratio = fba_count / len(top_products) * 100 if top_products else 0
        if fba_ratio > 80:
            factors["fba_dominance"] = {"score": 75, "detail": f"FBA 占比 {fba_ratio:.0f}%，专业卖家主导"}
        elif fba_ratio > 50:
            factors["fba_dominance"] = {"score": 45, "detail": f"FBA 占比 {fba_ratio:.0f}%，混合竞争"}
        else:
            factors["fba_dominance"] = {"score": 20, "detail": f"FBA 占比 {fba_ratio:.0f}%，非专业卖家多"}

        # 计算综合难度分数（加权平均）
        weights = {
            "review_barrier": 0.30,
            "quality_bar": 0.15,
            "brand_monopoly": 0.25,
            "price_competition": 0.15,
            "fba_dominance": 0.15,
        }

        total_score = 0
        total_weight = 0
        for factor_name, weight in weights.items():
            if factor_name in factors:
                total_score += factors[factor_name]["score"] * weight
                total_weight += weight

        difficulty_score = int(total_score / total_weight) if total_weight > 0 else 50

        # 难度等级
        if difficulty_score >= 80:
            level = "Very Hard"
            recommendation = "该关键词竞争极其激烈，建议寻找细分长尾词或差异化切入点。"
        elif difficulty_score >= 60:
            level = "Hard"
            recommendation = "竞争较强，需要较高的产品质量和营销预算。建议关注差评中的痛点进行差异化。"
        elif difficulty_score >= 40:
            level = "Medium"
            recommendation = "竞争适中，有一定机会。建议通过 Listing 优化和精准 PPC 投放切入。"
        elif difficulty_score >= 20:
            level = "Easy"
            recommendation = "竞争较弱，是不错的入场机会。但需验证搜索量是否足够。"
        else:
            level = "Very Easy"
            recommendation = "几乎没有竞争，但需警惕搜索量过低或品类限制。"

        result.update({
            "difficulty_score": difficulty_score,
            "difficulty_level": level,
            "factors": factors,
            "recommendation": recommendation,
        })

        return result

    # ================================================================
    # 关键词分组和优先级排序
    # ================================================================

    def prioritize_keywords(self, keywords: list[dict],
                             products_by_keyword: dict = None) -> list[dict]:
        """
        对关键词列表进行优先级排序

        综合考虑搜索量估算、竞争难度、商业价值等因素。

        :param keywords: 关键词列表 [{"keyword": "...", ...}]
        :param products_by_keyword: {keyword: [products]} 映射
        :return: 排序后的关键词列表（含优先级分数）
        """
        products_by_keyword = products_by_keyword or {}
        scored_keywords = []

        for kw_data in keywords:
            keyword = kw_data.get("keyword", "")
            if not keyword:
                continue

            products = products_by_keyword.get(keyword, [])

            # 估算搜索量
            volume = self.estimate_search_volume(keyword, products)
            est_searches = volume.get("estimated_monthly_searches", 0)

            # 评估难度
            difficulty = self.assess_keyword_difficulty(keyword, products)
            diff_score = difficulty.get("difficulty_score", 50)

            # 计算商业价值（基于平均价格和搜索量）
            avg_price = volume.get("details", {}).get("avg_price", 0)
            commercial_value = est_searches * avg_price * 0.12  # 搜索量 × 均价 × 转化率

            # 综合优先级分数: 高搜索量 + 低难度 + 高商业价值
            # 归一化: 搜索量 0-100, 难度反转 0-100, 商业价值 0-100
            volume_score = min(est_searches / 100, 100)  # 10000 搜索量 = 100 分
            ease_score = 100 - diff_score  # 难度越低分越高
            value_score = min(commercial_value / 500, 100)  # $50000 商业价值 = 100 分

            priority_score = (
                volume_score * 0.35 +
                ease_score * 0.35 +
                value_score * 0.30
            )

            scored_keywords.append({
                **kw_data,
                "estimated_monthly_searches": est_searches,
                "difficulty_score": diff_score,
                "difficulty_level": difficulty.get("difficulty_level", "Medium"),
                "commercial_value": round(commercial_value, 2),
                "priority_score": round(priority_score, 1),
                "avg_price": avg_price,
            })

        # 按优先级分数降序排列
        scored_keywords.sort(key=lambda x: x["priority_score"], reverse=True)

        return scored_keywords

    # ================================================================
    # AI 辅助关键词分析
    # ================================================================

    def ai_keyword_analysis(self, seed_keyword: str,
                             keywords: list[dict]) -> dict:
        """
        使用 AI 对关键词列表进行智能分析

        :param seed_keyword: 种子关键词
        :param keywords: 关键词列表
        :return: AI 分析结果
        """
        if not self.ai_client:
            return {"error": "AI client not configured"}

        # 准备关键词摘要
        kw_list = [kw.get("keyword", "") for kw in keywords[:50]]

        prompt = f"""你是一位 Amazon 选品专家。请分析以下关键词列表，给出选品建议。

种子关键词: {seed_keyword}
市场: Amazon {self.marketplace}

关键词列表:
{json.dumps(kw_list, ensure_ascii=False, indent=2)}

请分析:
1. 关键词聚类: 将关键词分为 3-5 个主题组
2. 市场机会: 哪些关键词组合暗示了未被满足的需求
3. 差异化方向: 基于关键词模式，建议 2-3 个差异化产品方向
4. 避坑建议: 哪些关键词可能有品牌/专利/合规风险

请用 JSON 格式返回:
{{
    "clusters": [{{"name": "组名", "keywords": ["kw1", "kw2"], "opportunity": "机会描述"}}],
    "opportunities": ["机会1", "机会2"],
    "differentiation": ["方向1", "方向2"],
    "risks": ["风险1", "风险2"]
}}"""

        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content.strip()

            # 尝试解析 JSON
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"raw_analysis": content}

        except Exception as e:
            logger.error(f"AI 关键词分析失败: {e}")
            return {"error": str(e)}

    # ================================================================
    # 完整关键词研究流程
    # ================================================================

    def full_research(self, seed_keyword: str,
                       products: list[dict] = None) -> dict:
        """
        执行完整的关键词研究流程

        :param seed_keyword: 种子关键词
        :param products: 搜索结果产品列表
        :return: 完整研究报告
        """
        logger.info(f"开始关键词研究: {seed_keyword}")

        # 1. 获取自动补全建议
        autocomplete = self.get_autocomplete_suggestions(seed_keyword, max_depth=1)

        # 2. 生成长尾关键词
        long_tails = self.generate_long_tail_keywords(seed_keyword)

        # 3. 合并所有关键词
        all_keywords = [{"keyword": seed_keyword, "source": "seed"}]
        all_keywords.extend(autocomplete)
        all_keywords.extend(long_tails)

        # 4. 去重
        seen = set()
        unique_keywords = []
        for kw in all_keywords:
            keyword = kw.get("keyword", "").lower().strip()
            if keyword and keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(kw)

        # 5. 搜索量估算（种子词）
        volume = self.estimate_search_volume(seed_keyword, products)

        # 6. 竞争难度评估（种子词）
        difficulty = self.assess_keyword_difficulty(seed_keyword, products)

        # 7. AI 分析（如果可用）
        ai_analysis = {}
        if self.ai_client:
            ai_analysis = self.ai_keyword_analysis(seed_keyword, unique_keywords)

        report = {
            "seed_keyword": seed_keyword,
            "marketplace": self.marketplace,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_keywords": len(unique_keywords),
                "autocomplete_count": len(autocomplete),
                "long_tail_count": len(long_tails),
                "estimated_monthly_searches": volume.get("estimated_monthly_searches", 0),
                "difficulty_score": difficulty.get("difficulty_score", 50),
                "difficulty_level": difficulty.get("difficulty_level", "Medium"),
            },
            "volume_analysis": volume,
            "difficulty_analysis": difficulty,
            "keywords": unique_keywords[:200],  # 限制返回数量
            "ai_analysis": ai_analysis,
        }

        logger.info(
            f"关键词研究完成: {len(unique_keywords)} 个关键词, "
            f"搜索量≈{volume.get('estimated_monthly_searches', 0)}, "
            f"难度={difficulty.get('difficulty_level', 'Medium')}"
        )

        return report
