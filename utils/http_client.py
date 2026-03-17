"""
Coupang 选品系统 - HTTP 请求工具
封装请求头管理、代理轮换、重试机制、频率控制
"""

import os
import time
import random
import requests
from typing import Optional
from utils.logger import get_logger

logger = get_logger()

# 常用 User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Coupang 专用请求头
COUPANG_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
}


class HttpClient:
    """HTTP 请求客户端，内置反爬虫策略"""

    def __init__(self, proxy: Optional[str] = None, min_delay: float = 1.0, max_delay: float = 3.0):
        self.session = requests.Session()
        self.proxy = proxy or os.getenv("PROXY_URL")
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request_time = 0

        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}
            logger.info(f"已配置代理: {self.proxy[:20]}...")

    def _get_headers(self, extra_headers: dict = None) -> dict:
        """生成随机化的请求头"""
        headers = {**COUPANG_HEADERS}
        headers["User-Agent"] = random.choice(USER_AGENTS)
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _rate_limit(self):
        """请求频率控制，避免触发反爬"""
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"频率控制: 等待 {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def get(self, url: str, params: dict = None, headers: dict = None,
            max_retries: int = 3, timeout: int = 30) -> Optional[requests.Response]:
        """
        发送 GET 请求，带重试机制
        """
        self._rate_limit()

        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    headers=self._get_headers(headers),
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 403:
                    logger.warning(f"[{attempt}/{max_retries}] 403 Forbidden: {url}")
                    time.sleep(random.uniform(5, 10))
                elif resp.status_code == 429:
                    logger.warning(f"[{attempt}/{max_retries}] 429 Too Many Requests, 等待...")
                    time.sleep(random.uniform(10, 20))
                else:
                    logger.warning(f"[{attempt}/{max_retries}] HTTP {resp.status_code}: {url}")

            except requests.exceptions.Timeout:
                logger.warning(f"[{attempt}/{max_retries}] 请求超时: {url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[{attempt}/{max_retries}] 连接错误: {url}")
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.error(f"[{attempt}/{max_retries}] 请求异常: {e}")

        logger.error(f"请求失败(已重试{max_retries}次): {url}")
        return None

    def post(self, url: str, data: dict = None, json_data: dict = None,
             headers: dict = None, max_retries: int = 3, timeout: int = 30) -> Optional[requests.Response]:
        """发送 POST 请求"""
        self._rate_limit()

        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.post(
                    url,
                    data=data,
                    json=json_data,
                    headers=self._get_headers(headers),
                    timeout=timeout,
                )
                if resp.status_code in (200, 201):
                    return resp
                else:
                    logger.warning(f"[{attempt}/{max_retries}] POST HTTP {resp.status_code}: {url}")
            except Exception as e:
                logger.error(f"[{attempt}/{max_retries}] POST 异常: {e}")
                time.sleep(random.uniform(2, 5))

        logger.error(f"POST 请求失败: {url}")
        return None

    def download_image(self, url: str, save_path: str) -> bool:
        """下载图片到本地"""
        try:
            resp = self.get(url, timeout=60)
            if resp and resp.content:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                logger.debug(f"图片已下载: {save_path}")
                return True
        except Exception as e:
            logger.error(f"图片下载失败: {e}")
        return False

    def close(self):
        """关闭会话"""
        self.session.close()
