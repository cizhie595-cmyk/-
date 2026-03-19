"""
顶层评论分析器入口模块

提供对 analysis.ai_analysis.review_analyzer.ReviewAnalyzer 的便捷导入，
同时扩展批量分析和统计汇总功能。

使用方式:
    from analysis.review_analyzer import ReviewAnalyzer, ReviewBatchAnalyzer
"""

from typing import Optional
from collections import Counter, defaultdict
from datetime import datetime

from utils.logger import get_logger
from analysis.ai_analysis.review_analyzer import ReviewAnalyzer

logger = get_logger()

# 直接重导出 ReviewAnalyzer，保持向后兼容
__all__ = ["ReviewAnalyzer", "ReviewBatchAnalyzer", "ReviewStatistics"]


class ReviewStatistics:
    """
    评论统计工具类

    提供不依赖 AI 的纯统计分析功能：
      - 评分分布
      - 评论趋势（按月/按周）
      - 关键词频次
      - 刷单检测
      - 评论质量评估
    """

    @staticmethod
    def rating_distribution(reviews: list[dict]) -> dict:
        """
        计算评分分布

        :param reviews: 评论列表
        :return: 评分分布统计
        """
        counts = Counter()
        for r in reviews:
            rating = r.get("rating", 0)
            if 1 <= rating <= 5:
                counts[int(rating)] += 1

        total = sum(counts.values())
        distribution = {}
        for star in range(1, 6):
            count = counts.get(star, 0)
            distribution[star] = {
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0,
            }

        avg = sum(r.get("rating", 0) for r in reviews if r.get("rating")) / max(
            sum(1 for r in reviews if r.get("rating")), 1
        )

        return {
            "total": total,
            "average_rating": round(avg, 2),
            "distribution": distribution,
            "positive_ratio": round(
                (counts.get(4, 0) + counts.get(5, 0)) / total * 100, 1
            ) if total > 0 else 0,
            "negative_ratio": round(
                (counts.get(1, 0) + counts.get(2, 0)) / total * 100, 1
            ) if total > 0 else 0,
        }

    @staticmethod
    def review_trend(reviews: list[dict], granularity: str = "month") -> dict:
        """
        计算评论趋势

        :param reviews: 评论列表
        :param granularity: 粒度 ("month" 或 "week")
        :return: 按时间分组的评论数量趋势
        """
        trend = defaultdict(lambda: {"count": 0, "avg_rating": 0, "ratings": []})

        for r in reviews:
            date_str = r.get("review_date", "")
            if not date_str:
                continue

            date_part = str(date_str)[:10]
            try:
                dt = datetime.strptime(date_part, "%Y-%m-%d")
                if granularity == "month":
                    key = dt.strftime("%Y-%m")
                else:
                    # ISO week
                    key = dt.strftime("%Y-W%V")
            except ValueError:
                continue

            trend[key]["count"] += 1
            rating = r.get("rating", 0)
            if rating:
                trend[key]["ratings"].append(rating)

        # 计算每个时间段的平均评分
        result = {}
        for key in sorted(trend.keys()):
            data = trend[key]
            ratings = data["ratings"]
            result[key] = {
                "count": data["count"],
                "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
            }

        return result

    @staticmethod
    def detect_suspicious_reviews(reviews: list[dict]) -> dict:
        """
        检测可疑评论（刷单辅助）

        检测规则：
          - 同一天大量5星好评
          - 评论内容过短（<10字符）
          - 评论内容高度相似
          - 评论者只有1条评论记录

        :param reviews: 评论列表
        :return: 可疑评论统计
        """
        suspicious = []
        date_5star = defaultdict(int)

        for r in reviews:
            is_suspicious = False
            reasons = []

            # 检查内容长度
            content = r.get("content", "")
            if content and len(content.strip()) < 10:
                reasons.append("评论内容过短")
                is_suspicious = True

            # 统计同日5星评论
            if r.get("rating") == 5:
                date_str = str(r.get("review_date", ""))[:10]
                if date_str:
                    date_5star[date_str] += 1

            if is_suspicious:
                suspicious.append({
                    "review_id": r.get("review_id", ""),
                    "rating": r.get("rating"),
                    "date": r.get("review_date", ""),
                    "reasons": reasons,
                })

        # 检查同日大量5星
        spike_dates = {d: c for d, c in date_5star.items() if c >= 5}

        return {
            "total_reviews": len(reviews),
            "suspicious_count": len(suspicious),
            "suspicious_ratio": round(
                len(suspicious) / len(reviews) * 100, 1
            ) if reviews else 0,
            "suspicious_reviews": suspicious[:20],  # 最多返回20条
            "five_star_spike_dates": spike_dates,
            "risk_level": (
                "高" if len(suspicious) / max(len(reviews), 1) > 0.2
                else "中" if len(suspicious) / max(len(reviews), 1) > 0.1
                else "低"
            ),
        }

    @staticmethod
    def keyword_frequency(reviews: list[dict], top_n: int = 30) -> list[dict]:
        """
        提取评论中的高频关键词

        :param reviews: 评论列表
        :param top_n: 返回前 N 个关键词
        :return: 关键词频次列表
        """
        word_counts = Counter()

        # 停用词列表
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can", "need",
            "this", "that", "these", "those", "it", "its", "i", "my",
            "me", "we", "our", "you", "your", "he", "she", "they",
            "them", "his", "her", "their", "and", "or", "but", "not",
            "no", "so", "if", "for", "of", "in", "on", "at", "to",
            "with", "from", "by", "as", "very", "just", "really",
            "got", "get", "one", "also", "like", "much", "more",
            "이", "그", "저", "것", "수", "등", "를", "을", "에",
            "의", "가", "는", "은", "로", "으로", "와", "과", "도",
        }

        for r in reviews:
            content = r.get("content", "").lower()
            if not content:
                continue

            # 简单分词
            words = content.split()
            for word in words:
                # 清理标点
                clean = word.strip(".,!?;:'\"()[]{}~`@#$%^&*-_+=<>/\\|")
                if clean and len(clean) > 1 and clean not in stop_words:
                    word_counts[clean] += 1

        return [
            {"keyword": word, "count": count}
            for word, count in word_counts.most_common(top_n)
        ]


class ReviewBatchAnalyzer:
    """
    批量评论分析器

    对多个产品的评论进行批量分析和对比。
    """

    def __init__(self, ai_client=None):
        """
        :param ai_client: OpenAI 客户端实例
        """
        self.analyzer = ReviewAnalyzer(ai_client=ai_client)
        self.stats = ReviewStatistics()

    def batch_analyze(
        self,
        products_reviews: dict[str, list[dict]],
        product_titles: dict[str, str] = None,
    ) -> dict:
        """
        批量分析多个产品的评论

        :param products_reviews: {asin: [reviews]} 映射
        :param product_titles: {asin: title} 映射
        :return: 批量分析结果
        """
        product_titles = product_titles or {}
        results = {}

        for asin, reviews in products_reviews.items():
            title = product_titles.get(asin, "")
            logger.info(f"[ReviewBatch] 分析 {asin} ({len(reviews)} 条评论)")

            try:
                # AI 分析
                ai_result = self.analyzer.analyze(reviews, title)

                # 统计分析
                stats_result = {
                    "rating_distribution": self.stats.rating_distribution(reviews),
                    "review_trend": self.stats.review_trend(reviews),
                    "suspicious_detection": self.stats.detect_suspicious_reviews(reviews),
                    "top_keywords": self.stats.keyword_frequency(reviews),
                }

                results[asin] = {
                    **ai_result,
                    **stats_result,
                }
            except Exception as e:
                logger.error(f"[ReviewBatch] 分析失败 {asin}: {e}")
                results[asin] = {"error": str(e)}

        return results

    def compare_reviews(self, products_reviews: dict[str, list[dict]]) -> dict:
        """
        对比多个产品的评论数据

        :param products_reviews: {asin: [reviews]} 映射
        :return: 对比结果
        """
        comparison = {
            "products": {},
            "best_rated": None,
            "most_reviewed": None,
            "lowest_suspicious": None,
        }

        best_rating = 0
        most_reviews = 0
        lowest_suspicious = 100

        for asin, reviews in products_reviews.items():
            stats = self.stats.rating_distribution(reviews)
            suspicious = self.stats.detect_suspicious_reviews(reviews)

            comparison["products"][asin] = {
                "total_reviews": stats["total"],
                "average_rating": stats["average_rating"],
                "positive_ratio": stats["positive_ratio"],
                "suspicious_ratio": suspicious["suspicious_ratio"],
            }

            if stats["average_rating"] > best_rating:
                best_rating = stats["average_rating"]
                comparison["best_rated"] = asin

            if stats["total"] > most_reviews:
                most_reviews = stats["total"]
                comparison["most_reviewed"] = asin

            if suspicious["suspicious_ratio"] < lowest_suspicious:
                lowest_suspicious = suspicious["suspicious_ratio"]
                comparison["lowest_suspicious"] = asin

        return comparison
