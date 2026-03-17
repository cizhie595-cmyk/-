"""
Coupang 选品系统 - 主流程控制器 (Pipeline)
功能: 串联所有模块，按步骤执行完整的选品分析流程
"""

import os
import sys
import json
from typing import Optional
from datetime import datetime

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t, set_language, get_language

from scrapers.coupang.search_crawler import CoupangSearchCrawler
from scrapers.coupang.detail_crawler import CoupangDetailCrawler
from scrapers.coupang.review_crawler import CoupangReviewCrawler
from scrapers.coupang.backend_crawler import CoupangBackendCrawler
from scrapers.alibaba1688.source_crawler import Alibaba1688Crawler

from analysis.data_filter import DataFilter
from analysis.ai_analysis.review_analyzer import ReviewAnalyzer
from analysis.ai_analysis.detail_analyzer import DetailPageAnalyzer
from analysis.profit_analysis.profit_calculator import ProfitCalculator
from analysis.market_analysis.category_analyzer import CategoryAnalyzer
from analysis.market_analysis.report_generator import ReportGenerator

logger = get_logger()


class SelectionPipeline:
    """
    选品分析主流程

    完整流程:
    Step 1: 搜索列表爬取 → 获取关键词下的产品列表
    Step 2: 后台数据匹配 → 获取点击量/销量等运营数据
    Step 3: 数据筛选 → 过滤不相关/低质量产品
    Step 4: 详情页爬取 → 获取产品详细信息
    Step 5: 评论爬取与分析 → 提取卖点/痛点/人群画像
    Step 6: 详情页AI分析 → 分析页面逻辑/视觉/信任
    Step 7: 类目趋势分析 → GMV/垄断/新品占比
    Step 8: 1688货源搜索 → 以图搜货确定成本
    Step 9: 利润计算 → 核算利润率/ROI
    Step 10: 生成报告 → 输出完整分析报告
    """

    def __init__(self, config: dict = None):
        """
        :param config: 配置字典
        """
        self.config = config or {}

        # 设置语言
        lang = self.config.get("language", "zh_CN")
        set_language(lang)

        # 初始化 AI 客户端
        self.ai_client = self._init_ai_client()

        # 初始化各模块
        self.http_client = HttpClient(
            min_delay=self.config.get("min_delay", 1.5),
            max_delay=self.config.get("max_delay", 3.0),
        )

        # 数据存储
        self.products = []
        self.daily_stats = {}
        self.review_analyses = {}
        self.detail_analyses = {}
        self.profit_results = []
        self.category_analysis = {}

    def _init_ai_client(self):
        """初始化 OpenAI 客户端"""
        api_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not configured, AI features will be disabled")
            return None

        try:
            from openai import OpenAI
            base_url = self.config.get("openai_base_url") or os.environ.get("OPENAI_BASE_URL")
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            return OpenAI(**kwargs)
        except ImportError:
            logger.warning("openai package not installed, run: pip install openai")
            return None

    def run(self, keyword: str, max_products: int = 50,
            skip_backend: bool = False,
            skip_1688: bool = False,
            wing_username: str = None,
            wing_password: str = None) -> str:
        """
        执行完整的选品分析流程

        :param keyword: 搜索关键词
        :param max_products: 最大产品数
        :param skip_backend: 是否跳过后台数据（无Wing账号时）
        :param skip_1688: 是否跳过1688搜货
        :param wing_username: Wing后台账号
        :param wing_password: Wing后台密码
        :return: 报告文件路径
        """
        logger.info(f"\n{'='*60}")
        logger.info(t("pipeline.start", keyword=keyword))
        logger.info(f"{'='*60}\n")

        start_time = datetime.now()

        try:
            # Step 1: 搜索列表爬取
            self._step_search(keyword, max_products)

            # Step 2: 后台数据匹配
            if not skip_backend and wing_username:
                self._step_backend(wing_username, wing_password)

            # Step 3: 数据筛选
            self._step_filter(keyword)

            # Step 4: 详情页爬取
            self._step_crawl_details()

            # Step 5: 评论爬取与分析
            self._step_review_analysis()

            # Step 6: 详情页AI分析
            self._step_detail_analysis()

            # Step 7: 类目趋势分析
            self._step_category_analysis(keyword)

            # Step 8: 1688货源搜索
            if not skip_1688:
                self._step_source_search()

            # Step 9: 利润计算
            self._step_profit_calculation()

            # Step 10: 生成报告
            report_path = self._step_generate_report(keyword)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"\n{'='*60}")
            logger.info(t("pipeline.complete", time=f"{elapsed:.1f}s"))
            logger.info(f"{'='*60}\n")

            return report_path

        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user")
            return ""
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            raise

    def _step_search(self, keyword: str, max_products: int):
        """Step 1: 搜索列表爬取"""
        logger.info(f"\n--- Step 1/10: {t('pipeline.step_search')} ---")

        crawler = CoupangSearchCrawler(http_client=self.http_client)
        try:
            self.products = crawler.search(keyword, max_pages=max_products // 20 + 1)
            self.products = self.products[:max_products]
            logger.info(f"Found {len(self.products)} products")
        finally:
            crawler.close()

    def _step_backend(self, username: str, password: str):
        """Step 2: 后台数据匹配"""
        logger.info(f"\n--- Step 2/10: {t('pipeline.step_backend')} ---")

        crawler = CoupangBackendCrawler(http_client=self.http_client)
        try:
            if crawler.login(username, password):
                self.products = crawler.match_products(self.products)
                self.daily_stats = crawler.batch_get_stats(self.products, days=30)
                logger.info(f"Got stats for {len(self.daily_stats)} products")
            else:
                logger.warning("Wing backend login failed, skipping backend data")
        finally:
            crawler.close()

    def _step_filter(self, keyword: str):
        """Step 3: 数据筛选"""
        logger.info(f"\n--- Step 3/10: {t('pipeline.step_filter')} ---")

        filter_rules = self.config.get("filter_rules", {})
        data_filter = DataFilter(rules=filter_rules)

        # 规则筛选
        result = data_filter.filter_products(self.products, self.daily_stats)

        # AI筛选（判断相关性）
        if self.ai_client:
            kept = data_filter.ai_filter(result["kept"], keyword, self.ai_client)
            result["kept"] = [p for p in kept if not p.get("is_filtered")]

        self.products = result["kept"]
        logger.info(f"After filtering: {len(self.products)} products remaining")

    def _step_crawl_details(self):
        """Step 4: 详情页爬取"""
        logger.info(f"\n--- Step 4/10: {t('pipeline.step_detail')} ---")

        crawler = CoupangDetailCrawler(http_client=self.http_client)
        try:
            for i, product in enumerate(self.products[:30]):  # 最多爬30个详情页
                url = product.get("url", "")
                if not url:
                    continue

                detail = crawler.crawl_detail(url, product.get("coupang_product_id", ""))
                if detail:
                    product.update(detail)
                    logger.debug(f"Detail [{i+1}/{min(len(self.products), 30)}] done")
        finally:
            crawler.close()

    def _step_review_analysis(self):
        """Step 5: 评论爬取与分析"""
        logger.info(f"\n--- Step 5/10: {t('pipeline.step_review')} ---")

        review_crawler = CoupangReviewCrawler(http_client=self.http_client)
        analyzer = ReviewAnalyzer(ai_client=self.ai_client)

        try:
            for i, product in enumerate(self.products[:20]):  # 最多分析20个产品的评论
                pid = product.get("coupang_product_id", "")
                if not pid:
                    continue

                # 爬取评论
                reviews = review_crawler.crawl_reviews(pid, max_pages=10)
                if not reviews:
                    continue

                # 刷单检测
                reviews = review_crawler.detect_suspicious_reviews(reviews)

                # AI分析
                analysis = analyzer.analyze(reviews, product.get("title", ""))
                self.review_analyses[pid] = analysis

                logger.debug(f"Review analysis [{i+1}] done: {len(reviews)} reviews")
        finally:
            review_crawler.close()

    def _step_detail_analysis(self):
        """Step 6: 详情页AI分析"""
        logger.info(f"\n--- Step 6/10: {t('pipeline.step_detail_ai')} ---")

        analyzer = DetailPageAnalyzer(ai_client=self.ai_client)

        for i, product in enumerate(self.products[:15]):  # 最多分析15个
            pid = product.get("coupang_product_id", "")
            detail_images = product.get("detail_images", [])

            analysis = analyzer.analyze(product, detail_images)
            self.detail_analyses[pid] = analysis

            logger.debug(f"Detail analysis [{i+1}] done")

    def _step_category_analysis(self, keyword: str):
        """Step 7: 类目趋势分析"""
        logger.info(f"\n--- Step 7/10: {t('pipeline.step_category')} ---")

        analyzer = CategoryAnalyzer(
            http_client=self.http_client,
            ai_client=self.ai_client,
            naver_client_id=self.config.get("naver_client_id"),
            naver_client_secret=self.config.get("naver_client_secret"),
        )

        try:
            self.category_analysis = analyzer.analyze_category(
                keyword, self.products, self.daily_stats
            )
        finally:
            analyzer.close()

    def _step_source_search(self):
        """Step 8: 1688货源搜索"""
        logger.info(f"\n--- Step 8/10: {t('pipeline.step_source')} ---")

        crawler = Alibaba1688Crawler(http_client=self.http_client)

        try:
            # 对Top产品进行以图搜货
            for product in self.products[:5]:
                images = product.get("images", [])
                main_img = next((img for img in images if img.get("type") == "main"), None)

                if main_img and main_img.get("local_path"):
                    sources = crawler.search_by_image(main_img["local_path"])
                else:
                    # 降级为关键词搜索
                    title = product.get("title", "")
                    if title:
                        sources = crawler.search_by_keyword(title[:20])
                    else:
                        sources = []

                product["sources_1688"] = sources
                logger.debug(f"Found {len(sources)} sources for product")
        finally:
            crawler.close()

    def _step_profit_calculation(self):
        """Step 9: 利润计算"""
        logger.info(f"\n--- Step 9/10: {t('pipeline.step_profit')} ---")

        profit_params = self.config.get("profit_params", {})
        calculator = ProfitCalculator(params=profit_params)

        for product in self.products[:10]:
            sources = product.get("sources_1688", [])
            price = product.get("price", 0)
            weight = product.get("weight_kg", 0.5)

            if sources and price:
                results = calculator.batch_compare(price, sources, weight)
                product["profit_analysis"] = results
                self.profit_results.extend(results[:3])  # 取每个产品的Top3货源

    def _step_generate_report(self, keyword: str) -> str:
        """Step 10: 生成报告"""
        logger.info(f"\n--- Step 10/10: {t('pipeline.step_report')} ---")

        generator = ReportGenerator(ai_client=self.ai_client)
        output_dir = self.config.get("output_dir", "reports")

        report_path = generator.generate(
            keyword=keyword,
            products=self.products,
            category_analysis=self.category_analysis,
            profit_results=self.profit_results,
            review_analyses=self.review_analyses,
            detail_analyses=self.detail_analyses,
            output_dir=output_dir,
        )

        return report_path

    def save_raw_data(self, keyword: str, output_dir: str = "data"):
        """保存原始数据到JSON文件"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        data = {
            "keyword": keyword,
            "timestamp": timestamp,
            "products": self.products,
            "daily_stats": self.daily_stats,
            "review_analyses": self.review_analyses,
            "detail_analyses": self.detail_analyses,
            "category_analysis": self.category_analysis,
            "profit_results": self.profit_results,
        }

        filepath = os.path.join(output_dir, f"raw_{keyword}_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Raw data saved to: {filepath}")
        return filepath
