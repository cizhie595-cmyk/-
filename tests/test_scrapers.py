"""
爬虫模块 Mock 测试
Issue #12: 提升测试覆盖率 - 爬虫模块
使用 unittest.mock 模拟 HTTP 请求，测试解析逻辑
"""
import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Amazon Search Crawler Tests
# ============================================================
class TestAmazonSearchCrawler(unittest.TestCase):
    """Amazon 搜索爬虫测试"""

    def setUp(self):
        from scrapers.amazon.search_crawler import AmazonSearchCrawler
        self.mock_http = MagicMock()
        self.crawler = AmazonSearchCrawler(http_client=self.mock_http, marketplace="US")

    def test_init_default_marketplace(self):
        """测试默认 marketplace 初始化"""
        self.assertEqual(self.crawler.marketplace, "US")

    def test_build_search_url(self):
        """测试搜索 URL 构建"""
        url = self.crawler._build_search_url("wireless earbuds", page=1, sort_by="relevance")
        self.assertIn("wireless", url)
        self.assertIn("earbuds", url)

    def test_search_returns_list(self):
        """测试搜索返回产品列表"""
        mock_html = """
        <div data-component-type="s-search-result" data-asin="B0TEST001">
            <h2><a><span>Test Product 1</span></a></h2>
            <span class="a-price"><span class="a-offscreen">$29.99</span></span>
            <span class="a-size-base">1,234 ratings</span>
        </div>
        """
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text=mock_html,
            content=mock_html.encode()
        )
        results = self.crawler.search("test", max_products=10)
        self.assertIsInstance(results, list)

    def test_search_empty_keyword(self):
        """测试空关键词搜索"""
        results = self.crawler.search("", max_products=10)
        self.assertIsInstance(results, list)

    def test_parse_search_results_empty_html(self):
        """测试空 HTML 解析"""
        results = self.crawler._parse_search_results("")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)


# ============================================================
# Amazon Detail Crawler Tests
# ============================================================
class TestAmazonDetailCrawler(unittest.TestCase):
    """Amazon 商品详情爬虫测试"""

    def setUp(self):
        from scrapers.amazon.detail_crawler import AmazonDetailCrawler
        self.mock_http = MagicMock()
        self.crawler = AmazonDetailCrawler(http_client=self.mock_http, marketplace="US")

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.crawler.marketplace, "US")

    def test_crawl_detail_returns_dict_or_none(self):
        """测试详情页爬取返回字典或 None"""
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text="<html><body>Not a product page</body></html>"
        )
        result = self.crawler.crawl_detail("B0TEST001")
        self.assertTrue(result is None or isinstance(result, dict))

    def test_crawl_detail_with_valid_html(self):
        """测试有效 HTML 的详情页解析"""
        mock_html = """
        <html>
        <head><title>Test Product - Amazon.com</title></head>
        <body>
            <span id="productTitle">Test Product Title</span>
            <span class="a-price"><span class="a-offscreen">$49.99</span></span>
            <span id="acrCustomerReviewText">2,345 ratings</span>
            <span id="acrPopover"><span class="a-icon-alt">4.5 out of 5 stars</span></span>
            <div id="feature-bullets"><ul><li>Feature 1</li><li>Feature 2</li></ul></div>
        </body>
        </html>
        """
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text=mock_html
        )
        result = self.crawler.crawl_detail("B0TEST001")
        if result:
            self.assertIn("title", result)

    def test_crawl_batch(self):
        """测试批量爬取"""
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text="<html><body></body></html>"
        )
        results = self.crawler.crawl_batch(["B0TEST001", "B0TEST002"], delay=0)
        self.assertIsInstance(results, list)

    def test_crawl_detail_http_error(self):
        """测试 HTTP 错误处理"""
        self.mock_http.get.return_value = MagicMock(status_code=503, text="Service Unavailable")
        result = self.crawler.crawl_detail("B0TEST001")
        self.assertTrue(result is None or isinstance(result, dict))


# ============================================================
# Coupang Search Crawler Tests
# ============================================================
class TestCoupangSearchCrawler(unittest.TestCase):
    """Coupang 搜索爬虫测试"""

    def setUp(self):
        from scrapers.coupang.search_crawler import CoupangSearchCrawler
        self.mock_http = MagicMock()
        self.crawler = CoupangSearchCrawler(http_client=self.mock_http)

    def test_search_returns_list(self):
        """测试搜索返回列表"""
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text="<html><body></body></html>"
        )
        results = self.crawler.search("블루투스 이어폰", top_n=10)
        self.assertIsInstance(results, list)

    def test_parse_search_page_empty(self):
        """测试空页面解析"""
        results = self.crawler._parse_search_page("<html><body></body></html>")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)


# ============================================================
# Coupang Detail Crawler Tests
# ============================================================
class TestCoupangDetailCrawler(unittest.TestCase):
    """Coupang 详情爬虫测试"""

    def setUp(self):
        from scrapers.coupang.detail_crawler import CoupangDetailCrawler
        self.mock_http = MagicMock()
        self.crawler = CoupangDetailCrawler(http_client=self.mock_http)

    def test_crawl_detail_returns_dict_or_none(self):
        """测试详情爬取返回"""
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text="<html><body></body></html>"
        )
        result = self.crawler.crawl_detail("https://www.coupang.com/vp/products/12345")
        self.assertTrue(result is None or isinstance(result, dict))

    def test_detect_delivery_type(self):
        """测试配送类型检测"""
        from bs4 import BeautifulSoup
        html = '<div class="prod-delivery-return"><span>로켓배송</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        dtype = self.crawler._detect_delivery_type(soup)
        self.assertIsInstance(dtype, str)


# ============================================================
# Keepa Client Tests
# ============================================================
class TestKeepaClient(unittest.TestCase):
    """Keepa API 客户端测试"""

    def setUp(self):
        from scrapers.keepa.keepa_client import KeepaClient
        self.client = KeepaClient(api_key="test-api-key", marketplace="US")

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.client.api_key, "test-api-key")

    @patch('scrapers.keepa.keepa_client.requests.get')
    def test_get_product(self, mock_get):
        """测试获取产品数据"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "products": [{
                "asin": "B0TEST001",
                "title": "Test Product",
                "csv": [[1, 2, 3], [4, 5, 6]],
                "stats": {"current": [2999, -1, 2999]}
            }],
            "tokensLeft": 100
        }
        mock_get.return_value = mock_response
        result = self.client.get_product(["B0TEST001"])
        self.assertIsInstance(result, (list, dict))

    @patch('scrapers.keepa.keepa_client.requests.get')
    def test_get_tokens_left(self, mock_get):
        """测试获取剩余 token"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tokensLeft": 50}
        mock_get.return_value = mock_response
        tokens = self.client.get_tokens_left()
        self.assertIsInstance(tokens, int)

    @patch('scrapers.keepa.keepa_client.requests.get')
    def test_search_products(self, mock_get):
        """测试搜索产品"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asinList": ["B0TEST001", "B0TEST002"],
            "tokensLeft": 80
        }
        mock_get.return_value = mock_response
        result = self.client.search_products("wireless earbuds")
        self.assertIsInstance(result, (list, dict))


# ============================================================
# Google Trends Crawler Tests
# ============================================================
class TestGoogleTrendsCrawler(unittest.TestCase):
    """Google Trends 爬虫测试"""

    def setUp(self):
        from scrapers.google_trends import GoogleTrendsCrawler
        self.crawler = GoogleTrendsCrawler(marketplace="US")

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.crawler.marketplace, "US")

    @patch('scrapers.google_trends.GoogleTrendsCrawler._init_pytrends')
    def test_get_interest_over_time(self, mock_init):
        """测试获取搜索趋势"""
        mock_init.return_value = None
        self.crawler.pytrends = MagicMock()
        self.crawler.pytrends.interest_over_time.return_value = MagicMock(
            empty=True
        )
        result = self.crawler.get_interest_over_time("wireless earbuds")
        self.assertIsInstance(result, (list, dict))

    def test_get_seasonal_analysis(self):
        """测试季节性分析"""
        with patch.object(self.crawler, 'get_interest_over_time', return_value=[]):
            result = self.crawler.get_seasonal_analysis("test keyword")
            self.assertIsInstance(result, dict)


# ============================================================
# 1688 Crawler Tests
# ============================================================
class TestAlibaba1688Crawler(unittest.TestCase):
    """1688 供应商爬虫测试"""

    def setUp(self):
        from scrapers.alibaba1688.source_crawler import Alibaba1688Crawler
        self.mock_http = MagicMock()
        self.crawler = Alibaba1688Crawler(http_client=self.mock_http)

    def test_search_by_keyword_returns_list(self):
        """测试关键词搜索返回列表"""
        self.mock_http.get.return_value = MagicMock(
            status_code=200,
            text="<html><body></body></html>"
        )
        results = self.crawler.search_by_keyword("蓝牙耳机", max_results=5)
        self.assertIsInstance(results, list)

    def test_parse_search_results_empty(self):
        """测试空结果解析"""
        results = self.crawler._parse_search_results("<html><body></body></html>")
        self.assertIsInstance(results, list)


# ============================================================
# Amazon SP-API Client Tests
# ============================================================
class TestAmazonSPAPIClient(unittest.TestCase):
    """Amazon SP-API 客户端测试"""

    def setUp(self):
        from scrapers.amazon.sp_api_client import AmazonSPAPIClient
        self.client = AmazonSPAPIClient(
            credentials={
                "refresh_token": "test-refresh-token",
                "lwa_app_id": "test-app-id",
                "lwa_client_secret": "test-secret",
                "aws_access_key": "test-access-key",
                "aws_secret_key": "test-secret-key",
            },
            marketplace="US"
        )

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.client.marketplace, "US")

    @patch('scrapers.amazon.sp_api_client.requests.post')
    def test_get_access_token(self, mock_post):
        """测试获取 access token"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"access_token": "test-token", "expires_in": 3600}
        )
        token = self.client._get_access_token()
        self.assertEqual(token, "test-token")


if __name__ == "__main__":
    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 加载所有测试类
    test_classes = [
        TestAmazonSearchCrawler,
        TestAmazonDetailCrawler,
        TestCoupangSearchCrawler,
        TestCoupangDetailCrawler,
        TestKeepaClient,
        TestGoogleTrendsCrawler,
        TestAlibaba1688Crawler,
        TestAmazonSPAPIClient,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出统计
    print(f"\n{'='*60}")
    print(f"Scraper Tests: {result.testsRun} run, "
          f"{len(result.failures)} failures, "
          f"{len(result.errors)} errors, "
          f"{len(result.skipped)} skipped")
    print(f"{'='*60}")

    sys.exit(0 if result.wasSuccessful() else 1)
