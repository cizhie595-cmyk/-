"""
Google Trends 趋势追踪模块
对应 PRD 3.4.1 - 行业趋势追踪

数据源: Google Trends API (pytrends 库) + Amazon Search Volume 历史数据
展示: 折线图 (Line Chart)，X 轴为过去 12 个月，Y 轴为搜索热度指数 (0-100)
"""

import os
import json
from typing import Optional
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger()


class GoogleTrendsCrawler:
    """
    Google Trends 趋势数据采集器

    使用 pytrends 库获取:
    - 关键词搜索热度趋势 (过去 12 个月)
    - 相关查询词
    - 地区热度分布
    - 关键词对比分析
    """

    # 亚马逊站点对应的 Google Trends 地区代码
    MARKETPLACE_GEO_MAP = {
        "US": "US",
        "UK": "GB",
        "DE": "DE",
        "JP": "JP",
        "FR": "FR",
        "IT": "IT",
        "ES": "ES",
        "CA": "CA",
        "AU": "AU",
        "IN": "IN",
    }

    # Google Trends 类目 ID (Shopping)
    SHOPPING_CATEGORY = 18

    def __init__(self, marketplace: str = "US", language: str = "en-US"):
        """
        :param marketplace: 亚马逊站点 (US/UK/DE/JP 等)
        :param language: 语言代码
        """
        self.marketplace = marketplace
        self.geo = self.MARKETPLACE_GEO_MAP.get(marketplace, "US")
        self.language = language
        self.pytrends = None
        self._init_pytrends()

    def _init_pytrends(self):
        """初始化 pytrends 客户端"""
        try:
            from pytrends.request import TrendReq
            self.pytrends = TrendReq(
                hl=self.language,
                tz=0,  # UTC
                timeout=(10, 30),
                retries=3,
                backoff_factor=1.0,
            )
            logger.info("Google Trends 客户端初始化成功")
        except ImportError:
            logger.warning(
                "pytrends 未安装，请运行: pip install pytrends"
            )
        except Exception as e:
            logger.warning(f"Google Trends 初始化失败: {e}")

    def get_interest_over_time(
        self,
        keywords: list,
        timeframe: str = "today 12-m",
        category: int = 0,
    ) -> dict:
        """
        获取关键词搜索热度趋势

        :param keywords: 关键词列表 (最多 5 个)
        :param timeframe: 时间范围 (默认过去 12 个月)
        :param category: Google Trends 类目 (0=所有, 18=Shopping)
        :return: {
            "keywords": list,
            "dates": list[str],
            "values": {keyword: list[int]},
            "averages": {keyword: float},
            "trend_direction": {keyword: "rising" | "declining" | "stable"},
        }
        """
        if not self.pytrends:
            return self._empty_trend_result(keywords)

        try:
            # pytrends 每次最多查 5 个关键词
            keywords = keywords[:5]

            self.pytrends.build_payload(
                kw_list=keywords,
                cat=category,
                timeframe=timeframe,
                geo=self.geo,
            )

            df = self.pytrends.interest_over_time()

            if df.empty:
                logger.warning(f"Google Trends 无数据: {keywords}")
                return self._empty_trend_result(keywords)

            # 解析结果
            dates = [d.strftime("%Y-%m-%d") for d in df.index]
            values = {}
            averages = {}
            trend_direction = {}

            for kw in keywords:
                if kw in df.columns:
                    vals = df[kw].tolist()
                    values[kw] = vals
                    averages[kw] = round(sum(vals) / len(vals), 1) if vals else 0

                    # 判断趋势方向
                    if len(vals) >= 4:
                        first_quarter = sum(vals[:len(vals)//4]) / (len(vals)//4)
                        last_quarter = sum(vals[-len(vals)//4:]) / (len(vals)//4)
                        if last_quarter > first_quarter * 1.15:
                            trend_direction[kw] = "rising"
                        elif last_quarter < first_quarter * 0.85:
                            trend_direction[kw] = "declining"
                        else:
                            trend_direction[kw] = "stable"
                    else:
                        trend_direction[kw] = "stable"

            result = {
                "keywords": keywords,
                "dates": dates,
                "values": values,
                "averages": averages,
                "trend_direction": trend_direction,
                "geo": self.geo,
                "timeframe": timeframe,
            }

            logger.info(
                f"Google Trends 数据获取成功: {keywords}, "
                f"{len(dates)} 个数据点"
            )
            return result

        except Exception as e:
            logger.error(f"Google Trends 查询失败: {e}")
            return self._empty_trend_result(keywords)

    def get_related_queries(self, keyword: str) -> dict:
        """
        获取相关查询词

        :return: {
            "top": [{"query": str, "value": int}],
            "rising": [{"query": str, "value": str}],
        }
        """
        if not self.pytrends:
            return {"top": [], "rising": []}

        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe="today 12-m",
                geo=self.geo,
            )

            related = self.pytrends.related_queries()

            result = {"top": [], "rising": []}

            if keyword in related:
                kw_data = related[keyword]

                if kw_data.get("top") is not None and not kw_data["top"].empty:
                    top_df = kw_data["top"].head(20)
                    result["top"] = [
                        {"query": row["query"], "value": int(row["value"])}
                        for _, row in top_df.iterrows()
                    ]

                if kw_data.get("rising") is not None and not kw_data["rising"].empty:
                    rising_df = kw_data["rising"].head(20)
                    result["rising"] = [
                        {"query": row["query"], "value": str(row["value"])}
                        for _, row in rising_df.iterrows()
                    ]

            logger.info(
                f"相关查询: top={len(result['top'])}, "
                f"rising={len(result['rising'])}"
            )
            return result

        except Exception as e:
            logger.error(f"获取相关查询失败: {e}")
            return {"top": [], "rising": []}

    def get_interest_by_region(self, keyword: str) -> list:
        """
        获取地区热度分布

        :return: [{"region": str, "value": int}]
        """
        if not self.pytrends:
            return []

        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe="today 12-m",
                geo=self.geo,
            )

            df = self.pytrends.interest_by_region(
                resolution="COUNTRY",
                inc_low_vol=True,
                inc_geo_code=True,
            )

            if df.empty:
                return []

            regions = []
            for region_name, row in df.iterrows():
                if row[keyword] > 0:
                    regions.append({
                        "region": region_name,
                        "value": int(row[keyword]),
                    })

            regions.sort(key=lambda x: x["value"], reverse=True)
            return regions[:30]

        except Exception as e:
            logger.error(f"获取地区热度失败: {e}")
            return []

    def get_seasonal_analysis(self, keyword: str) -> dict:
        """
        季节性分析 - 获取过去 5 年的月度数据，分析季节性规律

        :return: {
            "monthly_avg": {1: float, 2: float, ..., 12: float},
            "peak_months": list[int],
            "low_months": list[int],
            "seasonality_score": float,  # 0-1, 越高季节性越强
        }
        """
        if not self.pytrends:
            return {
                "monthly_avg": {},
                "peak_months": [],
                "low_months": [],
                "seasonality_score": 0,
            }

        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe="today 5-y",
                geo=self.geo,
            )

            df = self.pytrends.interest_over_time()

            if df.empty:
                return {
                    "monthly_avg": {},
                    "peak_months": [],
                    "low_months": [],
                    "seasonality_score": 0,
                }

            # 按月份汇总
            df["month"] = df.index.month
            monthly_avg = df.groupby("month")[keyword].mean()

            monthly_dict = {int(m): round(float(v), 1) for m, v in monthly_avg.items()}

            # 找出高峰和低谷月份
            avg_value = sum(monthly_dict.values()) / len(monthly_dict)
            peak_months = [m for m, v in monthly_dict.items() if v > avg_value * 1.2]
            low_months = [m for m, v in monthly_dict.items() if v < avg_value * 0.8]

            # 计算季节性得分 (标准差 / 均值)
            values = list(monthly_dict.values())
            if avg_value > 0:
                std_dev = (sum((v - avg_value) ** 2 for v in values) / len(values)) ** 0.5
                seasonality_score = min(round(std_dev / avg_value, 2), 1.0)
            else:
                seasonality_score = 0

            return {
                "monthly_avg": monthly_dict,
                "peak_months": peak_months,
                "low_months": low_months,
                "seasonality_score": seasonality_score,
            }

        except Exception as e:
            logger.error(f"季节性分析失败: {e}")
            return {
                "monthly_avg": {},
                "peak_months": [],
                "low_months": [],
                "seasonality_score": 0,
            }

    def get_comprehensive_trend(self, keyword: str) -> dict:
        """
        获取综合趋势分析（整合所有维度）

        :return: 包含趋势、相关词、地区、季节性的完整分析
        """
        result = {
            "keyword": keyword,
            "marketplace": self.marketplace,
            "geo": self.geo,
            "timestamp": datetime.now().isoformat(),
        }

        # 1. 搜索热度趋势
        result["interest_over_time"] = self.get_interest_over_time([keyword])

        # 2. 相关查询词
        result["related_queries"] = self.get_related_queries(keyword)

        # 3. 地区热度
        result["interest_by_region"] = self.get_interest_by_region(keyword)

        # 4. 季节性分析
        result["seasonal_analysis"] = self.get_seasonal_analysis(keyword)

        return result

    def _empty_trend_result(self, keywords: list) -> dict:
        """返回空的趋势结果"""
        return {
            "keywords": keywords,
            "dates": [],
            "values": {kw: [] for kw in keywords},
            "averages": {kw: 0 for kw in keywords},
            "trend_direction": {kw: "unknown" for kw in keywords},
            "geo": self.geo,
            "timeframe": "",
        }
