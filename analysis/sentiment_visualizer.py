"""
评论情感可视化器 - Step 5 增强模块
生成评论情感分析的可视化数据：词云、情感趋势、标签云、评分分布。
"""

import re
import math
from collections import Counter
from datetime import datetime
from typing import Optional
from loguru import logger


class SentimentVisualizer:
    """
    评论情感可视化器
    - 生成词频统计和词云数据
    - 情感趋势分析（按时间维度）
    - 评论标签/主题提取
    - 评分分布和情感比例分析
    - 评论质量评估
    """

    # 英文停用词
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "don", "now", "and", "but", "or", "if", "while", "this", "that",
        "these", "those", "i", "me", "my", "we", "our", "you", "your",
        "he", "him", "his", "she", "her", "it", "its", "they", "them",
        "their", "what", "which", "who", "whom", "up", "about", "get",
        "got", "one", "also", "really", "much", "well", "even", "back",
        "still", "way", "take", "come", "make", "like", "just", "know",
        "think", "see", "look", "want", "give", "use", "find", "tell",
        "thing", "product", "item", "bought", "buy", "purchase", "ordered",
        "order", "amazon", "review", "star", "stars",
    }

    # 情感词典
    POSITIVE_WORDS = {
        "great", "excellent", "amazing", "wonderful", "fantastic", "perfect",
        "love", "loved", "awesome", "best", "good", "nice", "beautiful",
        "quality", "sturdy", "durable", "comfortable", "recommend", "happy",
        "satisfied", "impressed", "solid", "reliable", "easy", "works",
        "worth", "value", "pleased", "enjoy", "convenient", "effective",
        "premium", "superb", "outstanding", "brilliant", "exceptional",
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "horrible", "awful", "worst", "poor", "cheap",
        "broke", "broken", "defective", "disappointed", "disappointing",
        "waste", "useless", "flimsy", "fragile", "return", "returned",
        "refund", "junk", "garbage", "fail", "failed", "failure",
        "uncomfortable", "difficult", "hard", "problem", "issue",
        "complaint", "wrong", "damaged", "missing", "fake", "scam",
        "overpriced", "misleading", "regret", "hate", "dislike",
    }

    def __init__(self, db=None):
        self.db = db

    # ------------------------------------------------------------------
    # 词云数据生成
    # ------------------------------------------------------------------
    def generate_word_cloud_data(self, reviews: list[dict],
                                  max_words: int = 100) -> list[dict]:
        """
        从评论中生成词云数据
        :param reviews: 评论列表，每条包含 text/body/content 字段
        :param max_words: 最大词数
        :return: 词频列表 [{word, count, sentiment, size}]
        """
        word_counts = Counter()

        for review in reviews:
            text = (
                review.get("text") or review.get("body")
                or review.get("content") or review.get("review_text", "")
            )
            if not text:
                continue

            words = self._tokenize(text)
            word_counts.update(words)

        # 过滤停用词和短词
        filtered = {
            w: c for w, c in word_counts.items()
            if w.lower() not in self.STOP_WORDS and len(w) > 2 and c >= 2
        }

        # 取 top N
        top_words = Counter(filtered).most_common(max_words)

        if not top_words:
            return []

        max_count = top_words[0][1]
        result = []
        for word, count in top_words:
            # 判断情感
            w_lower = word.lower()
            if w_lower in self.POSITIVE_WORDS:
                sentiment = "positive"
            elif w_lower in self.NEGATIVE_WORDS:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            # 计算词云大小 (10-60)
            size = max(10, round(count / max_count * 60))

            result.append({
                "word": word,
                "count": count,
                "sentiment": sentiment,
                "size": size,
            })

        return result

    # ------------------------------------------------------------------
    # 情感趋势分析
    # ------------------------------------------------------------------
    def analyze_sentiment_trend(self, reviews: list[dict]) -> dict:
        """
        按时间维度分析情感趋势
        :param reviews: 评论列表，每条包含 date 和 rating 字段
        :return: 情感趋势数据
        """
        result = {
            "labels": [],
            "positive_counts": [],
            "neutral_counts": [],
            "negative_counts": [],
            "avg_ratings": [],
            "total_reviews": len(reviews),
        }

        # 按月分组
        monthly_data = {}
        for review in reviews:
            date_str = review.get("date") or review.get("review_date", "")
            rating = review.get("rating") or review.get("star_rating", 0)

            month_key = self._extract_month(date_str)
            if not month_key:
                continue

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "positive": 0, "neutral": 0, "negative": 0,
                    "ratings": [], "count": 0,
                }

            # 情感分类（基于评分）
            try:
                r = float(rating)
            except (ValueError, TypeError):
                r = 0

            if r >= 4:
                monthly_data[month_key]["positive"] += 1
            elif r >= 3:
                monthly_data[month_key]["neutral"] += 1
            elif r > 0:
                monthly_data[month_key]["negative"] += 1

            if r > 0:
                monthly_data[month_key]["ratings"].append(r)
            monthly_data[month_key]["count"] += 1

        # 排序并生成序列
        for month in sorted(monthly_data.keys()):
            data = monthly_data[month]
            result["labels"].append(month)
            result["positive_counts"].append(data["positive"])
            result["neutral_counts"].append(data["neutral"])
            result["negative_counts"].append(data["negative"])
            avg_r = (
                round(sum(data["ratings"]) / len(data["ratings"]), 2)
                if data["ratings"] else 0
            )
            result["avg_ratings"].append(avg_r)

        return result

    # ------------------------------------------------------------------
    # 评论标签提取
    # ------------------------------------------------------------------
    def extract_review_tags(self, reviews: list[dict],
                             max_tags: int = 20) -> list[dict]:
        """
        从评论中提取主题标签
        :param reviews: 评论列表
        :param max_tags: 最大标签数
        :return: 标签列表 [{tag, count, sentiment, examples}]
        """
        # 预定义的产品属性标签模式
        tag_patterns = {
            "quality": r"\b(quality|well.?made|durable|sturdy|solid|build)\b",
            "price_value": r"\b(price|value|worth|money|cheap|expensive|affordable)\b",
            "size_fit": r"\b(size|fit|fits|small|large|big|tight|loose)\b",
            "comfort": r"\b(comfort|comfortable|uncomfortable|soft|hard|cushion)\b",
            "design": r"\b(design|look|looks|style|color|colour|appearance|beautiful)\b",
            "packaging": r"\b(packag|box|shipping|arrived|delivery|wrap)\b",
            "durability": r"\b(durable|durability|last|lasting|broke|broken|wear)\b",
            "ease_of_use": r"\b(easy|simple|difficult|hard.?to|complicated|intuitive)\b",
            "material": r"\b(material|fabric|plastic|metal|wood|leather|rubber)\b",
            "smell_odor": r"\b(smell|odor|scent|fragrance|stink)\b",
            "noise": r"\b(noise|noisy|quiet|silent|loud|sound)\b",
            "battery": r"\b(battery|charge|charging|power|rechargeable)\b",
            "customer_service": r"\b(customer.?service|support|warranty|return|refund)\b",
            "instructions": r"\b(instruction|manual|assembly|setup|install)\b",
            "cleaning": r"\b(clean|cleaning|wash|washable|maintenance)\b",
        }

        tag_counts = Counter()
        tag_sentiments = {}
        tag_examples = {}

        for review in reviews:
            text = (
                review.get("text") or review.get("body")
                or review.get("content") or review.get("review_text", "")
            )
            if not text:
                continue

            rating = review.get("rating") or review.get("star_rating", 0)
            try:
                r = float(rating)
            except (ValueError, TypeError):
                r = 0

            text_lower = text.lower()
            for tag, pattern in tag_patterns.items():
                if re.search(pattern, text_lower):
                    tag_counts[tag] += 1

                    # 情感统计
                    if tag not in tag_sentiments:
                        tag_sentiments[tag] = {"positive": 0, "negative": 0, "neutral": 0}
                    if r >= 4:
                        tag_sentiments[tag]["positive"] += 1
                    elif r >= 3:
                        tag_sentiments[tag]["neutral"] += 1
                    elif r > 0:
                        tag_sentiments[tag]["negative"] += 1

                    # 保存示例
                    if tag not in tag_examples:
                        tag_examples[tag] = []
                    if len(tag_examples[tag]) < 3:
                        snippet = text[:150] + "..." if len(text) > 150 else text
                        tag_examples[tag].append(snippet)

        # 构建结果
        result = []
        for tag, count in tag_counts.most_common(max_tags):
            sentiments = tag_sentiments.get(tag, {})
            total = sum(sentiments.values())
            positive_ratio = sentiments.get("positive", 0) / max(total, 1)

            if positive_ratio > 0.6:
                overall_sentiment = "positive"
            elif positive_ratio < 0.4:
                overall_sentiment = "negative"
            else:
                overall_sentiment = "mixed"

            result.append({
                "tag": tag.replace("_", " ").title(),
                "tag_key": tag,
                "count": count,
                "sentiment": overall_sentiment,
                "positive_ratio": round(positive_ratio * 100),
                "examples": tag_examples.get(tag, []),
            })

        return result

    # ------------------------------------------------------------------
    # 评分分布分析
    # ------------------------------------------------------------------
    def analyze_rating_distribution(self, reviews: list[dict]) -> dict:
        """
        分析评分分布
        :param reviews: 评论列表
        :return: 评分分布数据
        """
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total = 0
        ratings_sum = 0

        for review in reviews:
            rating = review.get("rating") or review.get("star_rating", 0)
            try:
                r = int(float(rating))
            except (ValueError, TypeError):
                continue
            if 1 <= r <= 5:
                distribution[r] += 1
                total += 1
                ratings_sum += r

        avg_rating = round(ratings_sum / max(total, 1), 2)

        # 情感比例
        positive = distribution[4] + distribution[5]
        neutral = distribution[3]
        negative = distribution[1] + distribution[2]

        return {
            "distribution": distribution,
            "total_reviews": total,
            "avg_rating": avg_rating,
            "sentiment_ratio": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
                "positive_pct": round(positive / max(total, 1) * 100, 1),
                "neutral_pct": round(neutral / max(total, 1) * 100, 1),
                "negative_pct": round(negative / max(total, 1) * 100, 1),
            },
            "labels": ["1 Star", "2 Stars", "3 Stars", "4 Stars", "5 Stars"],
            "values": [distribution[1], distribution[2], distribution[3],
                       distribution[4], distribution[5]],
        }

    # ------------------------------------------------------------------
    # 评论质量评估
    # ------------------------------------------------------------------
    def assess_review_quality(self, reviews: list[dict]) -> dict:
        """
        评估评论的整体质量（检测刷评风险）
        :param reviews: 评论列表
        :return: 评论质量评估结果
        """
        total = len(reviews)
        if total == 0:
            return {"quality_score": 0, "risk_level": "unknown", "flags": []}

        flags = []
        quality_score = 100

        # 1. 评分分布异常检测
        dist = self.analyze_rating_distribution(reviews)
        five_star_pct = dist["distribution"][5] / max(total, 1) * 100
        one_star_pct = dist["distribution"][1] / max(total, 1) * 100

        if five_star_pct > 80:
            quality_score -= 20
            flags.append({
                "type": "rating_skew",
                "severity": "high",
                "message": f"5星评论占比异常高 ({five_star_pct:.0f}%)，可能存在刷好评",
            })
        elif five_star_pct > 70:
            quality_score -= 10
            flags.append({
                "type": "rating_skew",
                "severity": "medium",
                "message": f"5星评论占比偏高 ({five_star_pct:.0f}%)",
            })

        if one_star_pct > 30:
            quality_score -= 15
            flags.append({
                "type": "negative_spike",
                "severity": "high",
                "message": f"1星评论占比异常高 ({one_star_pct:.0f}%)，产品可能存在严重质量问题",
            })

        # 2. 评论长度分析
        lengths = []
        short_count = 0
        for review in reviews:
            text = (
                review.get("text") or review.get("body")
                or review.get("content") or review.get("review_text", "")
            )
            if text:
                length = len(text.split())
                lengths.append(length)
                if length < 10:
                    short_count += 1

        short_pct = short_count / max(total, 1) * 100
        if short_pct > 50:
            quality_score -= 15
            flags.append({
                "type": "short_reviews",
                "severity": "medium",
                "message": f"短评论占比过高 ({short_pct:.0f}%)，评论可信度降低",
            })

        avg_length = sum(lengths) / max(len(lengths), 1)

        # 3. 重复内容检测
        texts = []
        for review in reviews:
            text = (
                review.get("text") or review.get("body")
                or review.get("content") or review.get("review_text", "")
            )
            if text:
                texts.append(text.lower().strip())

        unique_texts = set(texts)
        duplicate_pct = (1 - len(unique_texts) / max(len(texts), 1)) * 100
        if duplicate_pct > 10:
            quality_score -= 20
            flags.append({
                "type": "duplicate_reviews",
                "severity": "high",
                "message": f"重复评论占比 {duplicate_pct:.0f}%，存在刷评嫌疑",
            })

        # 4. Verified Purchase 比例
        verified_count = sum(
            1 for r in reviews
            if r.get("verified_purchase") or r.get("verified", False)
        )
        verified_pct = verified_count / max(total, 1) * 100
        if verified_pct < 50 and total > 10:
            quality_score -= 10
            flags.append({
                "type": "low_verified",
                "severity": "medium",
                "message": f"已验证购买评论仅占 {verified_pct:.0f}%",
            })

        quality_score = max(0, quality_score)

        if quality_score >= 80:
            risk_level = "low"
        elif quality_score >= 60:
            risk_level = "medium"
        elif quality_score >= 40:
            risk_level = "high"
        else:
            risk_level = "critical"

        return {
            "quality_score": quality_score,
            "risk_level": risk_level,
            "total_reviews": total,
            "avg_review_length": round(avg_length),
            "verified_purchase_pct": round(verified_pct, 1),
            "duplicate_pct": round(duplicate_pct, 1),
            "flags": flags,
        }

    # ------------------------------------------------------------------
    # 综合可视化数据
    # ------------------------------------------------------------------
    def generate_full_visualization(self, reviews: list[dict]) -> dict:
        """
        生成完整的评论可视化数据包
        :param reviews: 评论列表
        :return: 综合可视化数据
        """
        return {
            "word_cloud": self.generate_word_cloud_data(reviews),
            "sentiment_trend": self.analyze_sentiment_trend(reviews),
            "review_tags": self.extract_review_tags(reviews),
            "rating_distribution": self.analyze_rating_distribution(reviews),
            "review_quality": self.assess_review_quality(reviews),
            "total_reviews": len(reviews),
            "generated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """分词"""
        text = re.sub(r"[^\w\s'-]", " ", text.lower())
        words = text.split()
        return [w.strip("'-") for w in words if len(w.strip("'-")) > 2]

    @staticmethod
    def _extract_month(date_str: str) -> Optional[str]:
        """从日期字符串中提取月份"""
        if not date_str:
            return None

        # 尝试多种日期格式
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y",
                     "%b %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m")
            except ValueError:
                continue

        # 尝试提取年月
        match = re.search(r"(\d{4})-(\d{2})", date_str)
        if match:
            return f"{match.group(1)}-{match.group(2)}"

        return None
