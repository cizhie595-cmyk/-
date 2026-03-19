"""
Amazon 选品系统 - 专用主流程控制器 (Amazon Pipeline)
对应 PRD 整体 - 串联 Amazon SP-API + Keepa + 深度分析的完整流程

与 pipeline.py (Coupang 版) 对应，专门处理 Amazon 平台的选品分析
"""

import os
import sys
import json
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger
from utils.http_client import HttpClient
from i18n import t, set_language, get_language

logger = get_logger()


class AmazonSelectionPipeline:
    """
    Amazon 选品分析主流程

    完整流程:
    Step 1: 产品搜索 → SP-API 或爬虫获取产品列表
    Step 2: 第三方数据增强 → Keepa/Rainforest 获取历史数据
    Step 3: 数据筛选 → 规则筛选 + AI 智能过滤
    Step 4: 详情页深度爬取 → 获取产品详细信息
    Step 5: 评论爬取与分析 → 提取卖点/痛点/人群画像
    Step 6: 视觉语义分析 → 分析 Listing 质量/信任锚点
    Step 7: 类目趋势分析 → BSR 趋势/新品占比/垄断度
    Step 8: 1688 货源搜索 → 以图搜货确定成本
    Step 9: FBA 利润计算 → 核算 FBA 费用/利润率/ROI
    Step 10: 生成综合决策报告
    """

    def __init__(self, config: dict = None, user_id: int = None):
        """
        :param config: 配置字典
        :param user_id: 用户 ID（传入后会从数据库读取用户配置）
        """
        self.config = config or {}
        self.user_id = user_id

        # 设置语言
        lang = self.config.get("language", "zh_CN")
        set_language(lang)

        # 初始化 AI 客户端
        self.ai_client = self._init_ai_client()
        self.ai_model = self._get_ai_model()

        # 初始化 HTTP 客户端
        self.http_client = HttpClient(
            min_delay=self.config.get("min_delay", 2.0),
            max_delay=self.config.get("max_delay", 4.0),
        )

        # 初始化 SP-API 客户端
        self.sp_api_client = self._init_sp_api()

        # 初始化 Keepa 客户端
        self.keepa_client = self._init_keepa()

        # 数据存储
        self.products = []
        self.keepa_data = {}
        self.review_analyses = {}
        self.detail_analyses = {}
        self.deep_analyses = {}
        self.profit_results = []
        self.category_analysis = {}
        self.marketplace = self.config.get("marketplace", "US")

    def _init_ai_client(self):
        """初始化 AI 客户端"""
        if self.user_id:
            try:
                from auth.ai_config import AIConfigManager
                client = AIConfigManager.create_client(self.user_id)
                if client:
                    return client
            except Exception as e:
                logger.warning(f"从数据库读取 AI 配置失败: {e}")

        api_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key 未配置，AI 功能将被禁用")
            return None

        try:
            from openai import OpenAI
            base_url = self.config.get("openai_base_url") or os.environ.get("OPENAI_BASE_URL")
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            return OpenAI(**kwargs)
        except ImportError:
            logger.warning("openai 包未安装")
            return None

    def _get_ai_model(self) -> str:
        """获取 AI 模型名称"""
        if self.user_id:
            try:
                from auth.ai_config import AIConfigManager
                return AIConfigManager.get_model_name(self.user_id)
            except Exception:
                pass
        return self.config.get("openai_model", "gpt-4o")

    def _init_sp_api(self):
        """初始化 Amazon SP-API 客户端"""
        try:
            from scrapers.amazon.sp_api_client import AmazonSPAPIClient

            credentials = self.config.get("sp_api_credentials")

            # 尝试从用户配置读取
            if not credentials and self.user_id:
                try:
                    from auth.api_keys_config import APIKeysConfigManager
                    config = APIKeysConfigManager.get_service_config(
                        self.user_id, "amazon_sp_api", decrypt=True
                    )
                    if config:
                        credentials = config.get("credentials")
                except Exception:
                    pass

            if credentials:
                return AmazonSPAPIClient(
                    credentials=credentials,
                    marketplace=self.marketplace,
                )
        except Exception as e:
            logger.warning(f"SP-API 初始化失败: {e}")

        return None

    def _init_keepa(self):
        """初始化 Keepa 客户端"""
        try:
            from scrapers.amazon.third_party_api import KeepaClient

            keepa_key = self.config.get("keepa_api_key")

            if not keepa_key and self.user_id:
                try:
                    from auth.api_keys_config import APIKeysConfigManager
                    config = APIKeysConfigManager.get_service_config(
                        self.user_id, "keepa", decrypt=True
                    )
                    if config:
                        keepa_key = config.get("api_key")
                except Exception:
                    pass

            if keepa_key:
                return KeepaClient(api_key=keepa_key, marketplace=self.marketplace)
        except Exception as e:
            logger.warning(f"Keepa 初始化失败: {e}")

        return None

    def run(
        self,
        keyword: str,
        max_products: int = 100,
        skip_keepa: bool = False,
        skip_1688: bool = False,
        skip_deep_analysis: bool = False,
    ) -> str:
        """
        执行完整的 Amazon 选品分析流程

        :param keyword: 搜索关键词
        :param max_products: 最大产品数
        :param skip_keepa: 是否跳过 Keepa 数据
        :param skip_1688: 是否跳过 1688 搜货
        :param skip_deep_analysis: 是否跳过深度分析
        :return: 报告文件路径
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Amazon 选品分析开始: {keyword}")
        logger.info(f"{'='*60}\n")

        start_time = datetime.now()

        try:
            # Step 1: 产品搜索
            self._step_search(keyword, max_products)

            # Step 2: 第三方数据增强
            if not skip_keepa and self.keepa_client:
                self._step_keepa_enrich()

            # Step 3: 数据筛选
            self._step_filter(keyword)

            # Step 4: 详情页深度爬取
            self._step_crawl_details()

            # Step 5: 评论爬取与分析
            self._step_review_analysis()

            # Step 6: 视觉语义分析 (Deep Analysis)
            if not skip_deep_analysis:
                self._step_deep_analysis()

            # Step 7: 类目趋势分析
            self._step_category_analysis(keyword)

            # Step 8: 1688 货源搜索
            if not skip_1688:
                self._step_source_search()

            # Step 9: FBA 利润计算
            self._step_profit_calculation()

            # Step 10: 生成报告
            report_path = self._step_generate_report(keyword)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"\n{'='*60}")
            logger.info(f"Amazon 选品分析完成，耗时 {elapsed:.1f}s")
            logger.info(f"{'='*60}\n")

            return report_path

        except KeyboardInterrupt:
            logger.warning("Pipeline 被用户中断")
            return ""
        except Exception as e:
            logger.error(f"Pipeline 错误: {e}", exc_info=True)
            raise

    # ============================================================
    # 各步骤实现
    # ============================================================

    def _step_search(self, keyword: str, max_products: int):
        """Step 1: 产品搜索"""
        logger.info(f"\n--- Step 1/10: 产品搜索 ---")

        # 优先使用 SP-API
        if self.sp_api_client:
            try:
                self.products = self.sp_api_client.search_catalog(
                    keyword, max_results=max_products
                )
                logger.info(f"SP-API 返回 {len(self.products)} 个产品")
                if self.products:
                    return
            except Exception as e:
                logger.warning(f"SP-API 搜索失败: {e}")

        # 降级到爬虫
        from scrapers.amazon.search_crawler import AmazonSearchCrawler
        crawler = AmazonSearchCrawler(
            http_client=self.http_client,
            marketplace=self.marketplace,
        )
        try:
            self.products = crawler.search(keyword, max_products=max_products)
            logger.info(f"爬虫返回 {len(self.products)} 个产品")
        finally:
            crawler.close()

    def _step_keepa_enrich(self):
        """Step 2: Keepa 数据增强"""
        logger.info(f"\n--- Step 2/10: Keepa 数据增强 ---")

        asins = [p.get("asin") for p in self.products if p.get("asin")]
        if not asins:
            return

        # Keepa 每次最多查询 100 个 ASIN
        batch_size = 100
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            try:
                keepa_results = self.keepa_client.get_product(batch)
                if keepa_results:
                    for item in keepa_results:
                        asin = item.get("asin")
                        if asin:
                            self.keepa_data[asin] = item
            except Exception as e:
                logger.warning(f"Keepa 查询失败: {e}")

        # 将 Keepa 数据合并到产品中
        for product in self.products:
            asin = product.get("asin")
            if asin and asin in self.keepa_data:
                keepa = self.keepa_data[asin]
                product["keepa_bsr_avg_30d"] = keepa.get("bsr_avg_30d")
                product["keepa_price_avg_30d"] = keepa.get("price_avg_30d")
                product["keepa_review_count_30d"] = keepa.get("review_count_30d")
                product["keepa_new_offer_count"] = keepa.get("new_offer_count")

        logger.info(f"Keepa 数据增强完成: {len(self.keepa_data)} 个产品")

    def _step_filter(self, keyword: str):
        """Step 3: 数据筛选"""
        logger.info(f"\n--- Step 3/10: 数据筛选 ---")

        from analysis.amazon_data_filter import AmazonDataFilter

        filter_rules = self.config.get("filter_rules", {})
        data_filter = AmazonDataFilter(rules=filter_rules)

        # 规则筛选
        result = data_filter.filter_products(self.products)

        # AI 筛选
        if self.ai_client:
            try:
                kept = data_filter.ai_filter(result["kept"], keyword, ai_client=self.ai_client)
                result["kept"] = [p for p in kept if not p.get("is_filtered")]
            except Exception as e:
                logger.warning(f"AI 筛选失败: {e}")

        self.products = result["kept"]
        logger.info(f"筛选后保留 {len(self.products)} 个产品")

    def _step_crawl_details(self):
        """Step 4: 详情页深度爬取"""
        logger.info(f"\n--- Step 4/10: 详情页爬取 ---")

        from scrapers.amazon.detail_crawler import AmazonDetailCrawler

        crawler = AmazonDetailCrawler(
            http_client=self.http_client,
            marketplace=self.marketplace,
        )

        try:
            for i, product in enumerate(self.products[:30]):
                asin = product.get("asin", "")
                if not asin:
                    continue

                detail = crawler.crawl_detail(asin)
                if detail:
                    product.update(detail)
                    logger.debug(f"详情页 [{i+1}/{min(len(self.products), 30)}] 完成")
        finally:
            crawler.close()

    def _step_review_analysis(self):
        """Step 5: 评论爬取与分析"""
        logger.info(f"\n--- Step 5/10: 评论分析 ---")

        from scrapers.amazon.review_crawler import AmazonReviewCrawler
        from analysis.ai_analysis.review_analyzer import ReviewAnalyzer

        review_crawler = AmazonReviewCrawler(
            http_client=self.http_client,
            marketplace=self.marketplace,
        )
        analyzer = ReviewAnalyzer(ai_client=self.ai_client)

        try:
            for i, product in enumerate(self.products[:20]):
                asin = product.get("asin", "")
                if not asin:
                    continue

                crawl_result = review_crawler.crawl_reviews(asin, max_reviews=200)
                if not crawl_result:
                    continue

                # crawl_reviews 返回 dict，提取评论列表
                reviews_list = crawl_result.get("reviews", []) if isinstance(crawl_result, dict) else crawl_result
                if not reviews_list:
                    continue

                # 刷单检测
                fake_suspects = review_crawler._detect_fake_reviews(reviews_list)

                # AI 分析 - 传入评论列表
                analysis = analyzer.analyze(reviews_list, product.get("title", ""))

                # 合并爬取统计信息到分析结果
                if isinstance(crawl_result, dict):
                    analysis["crawl_statistics"] = crawl_result.get("statistics", {})
                    analysis["fake_review_suspects"] = fake_suspects if isinstance(fake_suspects, list) else crawl_result.get("fake_review_suspects", [])
                    analysis["total_crawled"] = crawl_result.get("total_crawled", len(reviews_list))

                self.review_analyses[asin] = analysis

                logger.debug(f"评论分析 [{i+1}] 完成: {len(reviews_list)} 条评论")
        finally:
            review_crawler.close()

    def _step_deep_analysis(self):
        """Step 6: 视觉语义分析"""
        logger.info(f"\n--- Step 6/10: 深度分析 ---")

        from scrapers.amazon.deep_crawler import AmazonDeepCrawler

        crawler = AmazonDeepCrawler(
            http_client=self.http_client,
            ai_client=self.ai_client,
        )

        try:
            for i, product in enumerate(self.products[:10]):
                asin = product.get("asin", "")
                if not asin:
                    continue

                result = crawler.deep_analyze(asin)
                if result:
                    self.deep_analyses[asin] = result
                    logger.debug(f"深度分析 [{i+1}] 完成")
        finally:
            crawler.close()

    def _step_category_analysis(self, keyword: str):
        """Step 7: 类目趋势分析"""
        logger.info(f"\n--- Step 7/10: 类目趋势分析 ---")

        from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer

        # AmazonCategoryAnalyzer 只接受 ai_client 和 ai_model 参数
        analyzer = AmazonCategoryAnalyzer(
            ai_client=self.ai_client,
            ai_model=self.ai_model,
        )

        try:
            # analyze_category 签名: (products, keyword, trends_data=None)
            self.category_analysis = analyzer.analyze_category(
                self.products, keyword, self.keepa_data
            )
        except Exception as e:
            logger.warning(f"类目分析失败: {e}")

    def _step_source_search(self):
        """Step 8: 1688 货源搜索"""
        logger.info(f"\n--- Step 8/10: 1688 货源搜索 ---")

        import tempfile
        import requests as _requests
        from scrapers.alibaba1688.source_crawler import Alibaba1688Crawler

        crawler = Alibaba1688Crawler(http_client=self.http_client)

        try:
            for product in self.products[:5]:
                sources = []

                # 尝试以图搜货：从多种字段获取主图 URL
                main_image_url = (
                    product.get("main_image")
                    or product.get("main_image_url")
                    or product.get("image_url")
                    or ""
                )

                # 也检查旧的 images 数组格式
                if not main_image_url:
                    images = product.get("images", [])
                    main_img = next(
                        (img for img in images if img.get("type") == "main"),
                        None,
                    )
                    if main_img:
                        main_image_url = main_img.get("local_path") or main_img.get("url", "")

                # 如果有图片 URL，下载到临时文件后以图搜货
                if main_image_url and main_image_url.startswith("http"):
                    try:
                        resp = _requests.get(main_image_url, timeout=15,
                                             headers={"User-Agent": "Mozilla/5.0"})
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            suffix = ".jpg"
                            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                                tmp.write(resp.content)
                                tmp_path = tmp.name
                            sources = crawler.search_by_image(tmp_path)
                            os.remove(tmp_path)
                    except Exception as e:
                        logger.debug(f"图片下载/搜索失败: {e}")
                elif main_image_url and os.path.isfile(main_image_url):
                    # 本地文件路径
                    sources = crawler.search_by_image(main_image_url)

                # 降级为关键词搜索
                if not sources:
                    title = product.get("title", "")
                    if title:
                        # 提取核心关键词（去掉品牌名和无关修饰词）
                        search_term = title[:30]
                        sources = crawler.search_by_keyword(search_term)

                product["sources_1688"] = sources
                logger.debug(f"找到 {len(sources)} 个货源")
        finally:
            crawler.close()

    def _step_profit_calculation(self):
        """Step 9: FBA 利润计算"""
        logger.info(f"\n--- Step 9/10: FBA 利润计算 ---")

        from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator

        calculator = AmazonFBAProfitCalculator(
            marketplace=self.marketplace,
            exchange_rate=self.config.get("exchange_rate", 7.25),
        )

        for product in self.products[:10]:
            sources = product.get("sources_1688", [])
            price = product.get("price") or product.get("price_current", 0)

            if sources and price:
                for source in sources[:3]:
                    try:
                        params = {
                            "selling_price": float(price),
                            "sourcing_cost_rmb": float(source.get("price", 0)),
                            "weight_kg": product.get("weight_kg", 0.5),
                            "length_cm": product.get("length_cm", 20),
                            "width_cm": product.get("width_cm", 15),
                            "height_cm": product.get("height_cm", 10),
                            "category": product.get("category", "General"),
                        }
                        result = calculator.calculate_profit(params)
                        result["asin"] = product.get("asin")
                        result["source_url"] = source.get("url")
                        self.profit_results.append(result)
                    except Exception as e:
                        logger.debug(f"利润计算失败: {e}")

    def _step_generate_report(self, keyword: str) -> str:
        """Step 10: 生成报告"""
        logger.info(f"\n--- Step 10/10: 生成报告 ---")

        from analysis.market_analysis.report_generator import ReportGenerator

        generator = ReportGenerator(ai_client=self.ai_client, platform="amazon")
        output_dir = self.config.get("output_dir", "reports")

        report_path = generator.generate(
            keyword=keyword,
            products=self.products,
            category_analysis=self.category_analysis,
            profit_results=self.profit_results,
            review_analyses=self.review_analyses,
            detail_analyses={**self.detail_analyses, **self.deep_analyses},
            output_dir=output_dir,
        )

        return report_path

    def save_raw_data(self, keyword: str, output_dir: str = "data"):
        """保存原始数据到 JSON 文件"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        data = {
            "platform": "amazon",
            "marketplace": self.marketplace,
            "keyword": keyword,
            "timestamp": timestamp,
            "products": self.products,
            "keepa_data": self.keepa_data,
            "review_analyses": self.review_analyses,
            "detail_analyses": self.detail_analyses,
            "deep_analyses": self.deep_analyses,
            "category_analysis": self.category_analysis,
            "profit_results": self.profit_results,
        }

        filepath = os.path.join(output_dir, f"amazon_raw_{keyword}_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"原始数据已保存: {filepath}")
        return filepath
