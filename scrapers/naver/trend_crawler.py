"""
Naver 趋势爬虫
对应 PRD 3.4.1 - Naver 搜索趋势数据采集

功能:
    1. Naver DataLab 搜索趋势 API
    2. Naver Shopping Insight 爬取
    3. 关键词搜索量趋势分析
"""

import json
import time
import hashlib
from typing import Optional
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.http_client import HttpClient

logger = get_logger()


class NaverTrendCrawler:
    """
    Naver 搜索趋势爬虫

    支持两种数据源:
    1. Naver DataLab API (需要 Client ID/Secret)
    2. Naver Shopping Insight 网页爬取 (无需认证)
    """

    DATALAB_API_URL = "https://openapi.naver.com/v1/datalab/search"
    SHOPPING_INSIGHT_URL = "https://datalab.naver.com/shoppingInsight/sCategory.naver"
    SEARCH_AD_API_URL = "https://api.naver.com/keywordstool"

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        http_client: Optional[HttpClient] = None,
    ):
        """
        :param client_id: Naver API Client ID
        :param client_secret: Naver API Client Secret
        :param http_client: 共享的 HTTP 客户端
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.http = http_client or HttpClient(min_delay=1.0, max_delay=2.0)
        self._has_api = bool(client_id and client_secret)

    # ============================================================
    # 1. Naver DataLab API - 搜索趋势
    # ============================================================

    def get_search_trend(
        self,
        keywords: list[str],
        start_date: str = None,
        end_date: str = None,
        time_unit: str = "month",
        device: str = "",
        gender: str = "",
        ages: list[str] = None,
    ) -> Optional[dict]:
        """
        通过 Naver DataLab API 获取搜索趋势

        :param keywords: 关键词列表 (最多 5 个)
        :param start_date: 开始日期 (YYYY-MM-DD)
        :param end_date: 结束日期 (YYYY-MM-DD)
        :param time_unit: 时间粒度 (date/week/month)
        :param device: 设备类型 (pc/mo, 空=全部)
        :param gender: 性别 (m/f, 空=全部)
        :param ages: 年龄段列表
        :return: 趋势数据字典
        """
        if not self._has_api:
            logger.warning("Naver API 未配置，降级到网页爬取模式")
            return self._scrape_trend_page(keywords[0] if keywords else "")

        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # 构建请求体
        keyword_groups = []
        for kw in keywords[:5]:
            keyword_groups.append({
                "groupName": kw,
                "keywords": [kw],
            })

        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keyword_groups,
        }

        if device:
            body["device"] = device
        if gender:
            body["gender"] = gender
        if ages:
            body["ages"] = ages

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json",
        }

        try:
            import requests
            resp = requests.post(
                self.DATALAB_API_URL,
                headers=headers,
                json=body,
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                return self._parse_datalab_response(data, keywords)
            else:
                logger.error(f"Naver DataLab API 错误: {resp.status_code} - {resp.text}")
                return None

        except Exception as e:
            logger.error(f"Naver DataLab API 请求失败: {e}")
            return None

    def _parse_datalab_response(self, data: dict, keywords: list[str]) -> dict:
        """解析 DataLab API 响应"""
        results = data.get("results", [])
        parsed = {
            "keywords": keywords,
            "trends": {},
            "summary": {},
        }

        for result in results:
            keyword = result.get("title", "")
            data_points = result.get("data", [])

            trend_data = []
            for point in data_points:
                trend_data.append({
                    "period": point.get("period", ""),
                    "ratio": point.get("ratio", 0),
                })

            parsed["trends"][keyword] = trend_data

            # 计算趋势摘要
            if len(trend_data) >= 2:
                recent = trend_data[-1]["ratio"]
                previous = trend_data[-2]["ratio"]
                change_pct = ((recent - previous) / previous * 100) if previous > 0 else 0

                avg_ratio = sum(d["ratio"] for d in trend_data) / len(trend_data)
                max_ratio = max(d["ratio"] for d in trend_data)
                min_ratio = min(d["ratio"] for d in trend_data)

                parsed["summary"][keyword] = {
                    "latest_ratio": recent,
                    "previous_ratio": previous,
                    "change_pct": round(change_pct, 2),
                    "avg_ratio": round(avg_ratio, 2),
                    "max_ratio": max_ratio,
                    "min_ratio": min_ratio,
                    "trend_direction": "up" if change_pct > 5 else ("down" if change_pct < -5 else "stable"),
                }

        return parsed

    # ============================================================
    # 2. Naver Shopping Insight - 网页爬取 (无需 API)
    # ============================================================

    def get_shopping_trend(
        self,
        keyword: str,
        category_id: str = "",
        period: str = "1y",
    ) -> Optional[dict]:
        """
        爬取 Naver Shopping Insight 趋势数据

        :param keyword: 搜索关键词
        :param category_id: 类目 ID
        :param period: 时间范围 (1m/3m/1y/3y)
        :return: 购物趋势数据
        """
        try:
            params = {
                "cid": category_id,
                "timeUnit": "date" if period in ("1m", "3m") else "week",
                "startDate": self._period_to_start_date(period),
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "keyword": keyword,
            }

            resp = self.http.get(
                self.SHOPPING_INSIGHT_URL,
                params=params,
                headers={"Referer": "https://datalab.naver.com/"},
            )

            if resp and resp.status_code == 200:
                return self._parse_shopping_insight(resp.text, keyword)
            else:
                logger.warning(f"Naver Shopping Insight 请求失败")
                return None

        except Exception as e:
            logger.error(f"Naver Shopping Insight 爬取失败: {e}")
            return None

    def _parse_shopping_insight(self, html: str, keyword: str) -> dict:
        """解析 Shopping Insight 页面"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = {
            "keyword": keyword,
            "source": "naver_shopping_insight",
            "data_points": [],
            "category_distribution": [],
            "age_distribution": [],
            "gender_distribution": [],
        }

        # 尝试从页面中的 script 标签提取 JSON 数据
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.string or ""
            if "chartData" in text or "trendData" in text:
                try:
                    # 提取 JSON 数据
                    import re
                    json_match = re.search(r'var\s+\w+Data\s*=\s*(\{.*?\});', text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        if "data" in data:
                            result["data_points"] = data["data"]
                except (json.JSONDecodeError, AttributeError):
                    pass

        return result

    # ============================================================
    # 3. 关键词搜索量分析
    # ============================================================

    def get_keyword_volume(self, keywords: list[str]) -> list[dict]:
        """
        获取关键词搜索量数据

        :param keywords: 关键词列表
        :return: 每个关键词的搜索量数据
        """
        results = []

        for keyword in keywords:
            volume_data = {
                "keyword": keyword,
                "monthly_search_volume": None,
                "competition_level": None,
                "trend_12m": None,
            }

            # 尝试通过 DataLab API 获取趋势
            if self._has_api:
                trend = self.get_search_trend([keyword], time_unit="month")
                if trend and keyword in trend.get("summary", {}):
                    summary = trend["summary"][keyword]
                    volume_data["trend_12m"] = summary
                    volume_data["trend_direction"] = summary.get("trend_direction")

            results.append(volume_data)
            time.sleep(0.5)  # 避免请求过快

        return results

    def compare_keywords(self, keywords: list[str]) -> dict:
        """
        对比多个关键词的搜索趋势

        :param keywords: 关键词列表 (最多 5 个)
        :return: 对比结果
        """
        if self._has_api:
            return self.get_search_trend(keywords[:5])

        # 降级：逐个查询
        all_trends = {}
        for kw in keywords[:5]:
            trend = self._scrape_trend_page(kw)
            if trend:
                all_trends[kw] = trend
            time.sleep(1)

        return {
            "keywords": keywords[:5],
            "trends": all_trends,
            "source": "web_scraping",
        }

    # ============================================================
    # 辅助方法
    # ============================================================

    def _scrape_trend_page(self, keyword: str) -> Optional[dict]:
        """降级方案：爬取 Naver 趋势网页"""
        try:
            url = f"https://datalab.naver.com/keyword/trendSearch.naver"
            params = {"keyword": keyword}

            resp = self.http.get(url, params=params)
            if resp and resp.status_code == 200:
                return {"keyword": keyword, "source": "web_scraping", "raw_html_length": len(resp.text)}
            return None
        except Exception as e:
            logger.error(f"Naver 趋势页面爬取失败: {e}")
            return None

    def _period_to_start_date(self, period: str) -> str:
        """将时间范围转换为开始日期"""
        now = datetime.now()
        mapping = {
            "1m": timedelta(days=30),
            "3m": timedelta(days=90),
            "1y": timedelta(days=365),
            "3y": timedelta(days=1095),
        }
        delta = mapping.get(period, timedelta(days=365))
        return (now - delta).strftime("%Y-%m-%d")

    def close(self):
        """关闭 HTTP 客户端"""
        if self.http:
            self.http.close()
