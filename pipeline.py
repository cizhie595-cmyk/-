"""
Coupang 选品系统 - 主流程控制器 (Pipeline)
功能: 串联所有模块，按步骤执行完整的选品分析流程

增强版: 集成关键词研究、BSR追踪、竞品发现、情感可视化、
       供应商评分、定价优化、AI决策引擎、看板分析等模块
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
    选品分析主流程（Coupang 平台增强版）

    完整流程:
    Step 1:   搜索列表爬取 → 获取关键词下的产品列表
    Step 2:   后台数据匹配 → 获取点击量/销量等运营数据
    Step 3:   数据筛选 → 过滤不相关/低质量产品
    Step 3.5: 关键词研究 → 竞争度评估/搜索量估算/长尾词挖掘
    Step 4:   详情页爬取 → 获取产品详细信息
    Step 4.5: BSR 追踪 + 竞品发现 → 排名快照/竞争格局/市场空白
    Step 5:   评论爬取与分析 → 提取卖点/痛点/人群画像
    Step 5.5: 评论情感可视化 → 词云/情感趋势/标签提取/评分分布
    Step 6:   详情页AI分析 → 分析页面逻辑/视觉/信任
    Step 7:   类目趋势分析 → GMV/垄断/新品占比
    Step 8:   1688货源搜索 → 以图搜货确定成本
    Step 8.5: 供应商评分 → 多维度供应商可靠性评估
    Step 9:   利润计算 → 核算利润率/ROI
    Step 9.5: 定价策略优化 → 最优定价/弹性模拟/多策略对比
    Step 9.8: AI 选品决策 → 综合评分/GO-NOGO 决策/风险识别
    Step 10:  生成报告 → 输出完整分析报告（含所有增强模块数据）
    """

    def __init__(self, config: dict = None, user_id: int = None):
        """
        :param config: 配置字典
        :param user_id: 用户ID（传入后会从数据库动态读取该用户的 AI 配置）
        """
        self.config = config or {}
        self.user_id = user_id

        # 设置语言
        lang = self.config.get("language", "zh_CN")
        set_language(lang)

        # 初始化 AI 客户端（支持动态用户配置）
        self.ai_client = self._init_ai_client()
        self.ai_model = self._get_ai_model()

        # 初始化各模块
        self.http_client = HttpClient(
            min_delay=self.config.get("min_delay", 1.5),
            max_delay=self.config.get("max_delay", 3.0),
        )

        # 核心数据存储
        self.products = []
        self.daily_stats = {}
        self.review_analyses = {}
        self.detail_analyses = {}
        self.profit_results = []
        self.category_analysis = {}

        # 增强模块数据存储
        self.keyword_analysis = {}
        self.bsr_tracking = {}
        self.competitor_analysis = {}
        self.sentiment_analysis = {}
        self.supplier_scores = []
        self.pricing_analysis = {}
        self.decision_results = {}
        self.dashboard_data = {}

        # 平台标识
        self.platform = "coupang"
        self.marketplace = self.config.get("marketplace", "KR")

    def _init_ai_client(self):
        """
        初始化 OpenAI 兼容客户端

        优先级:
        1. 如果传入了 user_id，从数据库读取该用户的 AI 配置
        2. 如果 config 中直接传入了 api_key，使用 config 配置
        3. 最后回退到环境变量
        """
        # 方式 1: 从数据库动态读取用户配置
        if self.user_id:
            try:
                from auth.ai_config import AIConfigManager
                client = AIConfigManager.create_client(self.user_id)
                if client:
                    logger.info(f"使用用户 {self.user_id} 的 AI 配置初始化客户端")
                    return client
            except Exception as e:
                logger.warning(f"从数据库读取用户 AI 配置失败: {e}")

        # 方式 2: 从 config 字典读取
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

    def _get_ai_model(self) -> str:
        """
        获取用户配置的 AI 模型名称

        优先级: 用户数据库配置 > config 字典 > 默认值
        """
        if self.user_id:
            try:
                from auth.ai_config import AIConfigManager
                return AIConfigManager.get_model_name(self.user_id)
            except Exception:
                pass
        return self.config.get("openai_model", "gpt-4o")

    def run(self, keyword: str, max_products: int = 50,
            skip_backend: bool = False,
            skip_1688: bool = False,
            skip_enhanced: bool = False,
            wing_username: str = None,
            wing_password: str = None) -> str:
        """
        执行完整的选品分析流程

        :param keyword: 搜索关键词
        :param max_products: 最大产品数
        :param skip_backend: 是否跳过后台数据（无Wing账号时）
        :param skip_1688: 是否跳过1688搜货
        :param skip_enhanced: 是否跳过增强分析模块（快速模式）
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

            # Step 3.5: 关键词研究（增强）
            if not skip_enhanced:
                self._step_keyword_research(keyword)

            # Step 4: 详情页爬取
            self._step_crawl_details()

            # Step 4.5: BSR 追踪和竞品发现（增强）
            if not skip_enhanced:
                self._step_bsr_and_competitor()

            # Step 5: 评论爬取与分析
            self._step_review_analysis()

            # Step 5.5: 评论情感可视化（增强）
            if not skip_enhanced:
                self._step_sentiment_visualization()

            # Step 6: 详情页AI分析
            self._step_detail_analysis()

            # Step 7: 类目趋势分析
            self._step_category_analysis(keyword)

            # Step 8: 1688货源搜索
            if not skip_1688:
                self._step_source_search()

            # Step 8.5: 供应商评分（增强）
            if not skip_1688 and not skip_enhanced:
                self._step_supplier_scoring()

            # Step 9: 利润计算
            self._step_profit_calculation()

            # Step 9.5: 定价策略优化（增强）
            if not skip_enhanced:
                self._step_pricing_optimization(keyword)

            # Step 9.8: AI 选品决策评估（增强）
            if not skip_enhanced:
                self._step_decision_evaluation()

            # Step 10: 生成报告（含增强模块数据）
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

    # ============================================================
    # 核心步骤实现（Step 1 - Step 10）
    # ============================================================

    def _step_search(self, keyword: str, max_products: int):
        """Step 1: 搜索列表爬取"""
        logger.info(f"\n--- Step 1/10: {t('pipeline.step_search')} ---")

        crawler = CoupangSearchCrawler(http_client=self.http_client)
        try:
            self.products = crawler.search(keyword, top_n=max_products)
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

                    # 下载主图到本地，以支持 Step 8 以图搜货
                    pid = product.get("coupang_product_id", "")
                    images = product.get("images", [])
                    detail_images = product.get("detail_images", [])
                    if pid and images:
                        try:
                            saved = crawler.download_product_images(pid, images, detail_images)
                            # 将本地路径写回 images 数组
                            main_paths = saved.get("main", [])
                            for img in images:
                                if img.get("type") == "main" and main_paths:
                                    img["local_path"] = main_paths[0]
                                    break
                        except Exception as e:
                            logger.debug(f"图片下载失败: {e}")

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
        logger.info(f"\n--- Step 6/10: {t('pipeline.step_detail_analysis')} ---")

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
        """Step 10: 生成报告（含增强模块数据）"""
        logger.info(f"\n--- Step 10/10: {t('pipeline.step_report')} ---")

        generator = ReportGenerator(ai_client=self.ai_client, platform="coupang")
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

        # 如果有增强模块数据，追加到报告中
        if any([self.keyword_analysis, self.competitor_analysis,
                self.sentiment_analysis, self.pricing_analysis,
                self.decision_results, self.supplier_scores]):
            self._append_enhanced_report(report_path, keyword)

        return report_path

    # ============================================================
    # 增强步骤实现（新增模块）
    # ============================================================

    def _step_keyword_research(self, keyword: str):
        """Step 3.5: 关键词研究分析"""
        logger.info(f"\n--- Step 3.5: 关键词研究 ---")

        try:
            from analysis.keyword_researcher import KeywordResearcher
            researcher = KeywordResearcher(
                http_client=self.http_client,
                ai_client=self.ai_client,
                marketplace=self.marketplace,
            )

            # 关键词竞争度评估
            difficulty = researcher.assess_keyword_difficulty(keyword, self.products)
            self.keyword_analysis["difficulty"] = difficulty

            # 搜索量估算
            volume = researcher.estimate_search_volume(keyword, self.products)
            self.keyword_analysis["search_volume"] = volume

            # 长尾词挖掘
            long_tail = researcher.generate_long_tail_keywords(keyword)
            self.keyword_analysis["long_tail"] = long_tail

            # 关键词分组
            if long_tail:
                groups = researcher.group_keywords(long_tail)
                self.keyword_analysis["groups"] = groups

            logger.info(
                f"关键词分析: 竞争度 {difficulty.get('difficulty_score', 'N/A')}/100  "
                f"估算月搜索量 {volume.get('estimated_monthly_searches', 'N/A')}  "
                f"长尾词 {len(long_tail)} 个"
            )
        except Exception as e:
            logger.warning(f"关键词研究失败: {e}")

    def _step_bsr_and_competitor(self):
        """Step 4.5: BSR 追踪和竞品发现"""
        logger.info(f"\n--- Step 4.5: BSR 追踪和竞品发现 ---")

        # BSR 快照记录
        try:
            from analysis.bsr_tracker import BSRTracker
            tracker = BSRTracker(marketplace=self.marketplace)

            for product in self.products[:20]:
                pid = product.get("coupang_product_id", "")
                if not pid:
                    continue

                snapshot_data = {
                    "bsr_rank": product.get("bsr_rank") or product.get("bsr") or product.get("rank"),
                    "price": product.get("price") or product.get("price_current"),
                    "rating": product.get("rating"),
                    "review_count": product.get("review_count"),
                    "stock_status": product.get("stock_status", "in_stock"),
                    "category": product.get("category", ""),
                }

                snapshot = tracker.record_snapshot(
                    asin=pid,
                    snapshot_data=snapshot_data,
                )
                self.bsr_tracking[pid] = snapshot

            logger.info(f"BSR 快照已记录 {len(self.bsr_tracking)} 个产品")
        except Exception as e:
            logger.warning(f"BSR 追踪失败: {e}")

        # 竞品发现
        try:
            from analysis.competitor_finder import CompetitorFinder
            finder = CompetitorFinder(
                http_client=self.http_client,
                marketplace=self.marketplace,
            )

            if len(self.products) >= 2:
                # 竞争格局分析
                landscape = finder.analyze_landscape(products=self.products[:20])
                self.competitor_analysis = landscape
                logger.info(f"竞争格局分析完成")

                # 市场空白发现
                gaps = finder.find_market_gaps(products=self.products[:20])
                self.competitor_analysis["market_gaps"] = gaps
                logger.info(f"发现 {len(gaps.get('gaps', []))} 个市场空白")
        except Exception as e:
            logger.warning(f"竞品发现失败: {e}")

    def _step_sentiment_visualization(self):
        """Step 5.5: 评论情感可视化"""
        logger.info(f"\n--- Step 5.5: 评论情感可视化 ---")

        if not self.review_analyses:
            logger.info("无评论数据，跳过情感可视化")
            return

        try:
            from analysis.sentiment_visualizer import SentimentVisualizer
            visualizer = SentimentVisualizer()

            # 汇总所有评论
            all_reviews = []
            for pid, analysis in self.review_analyses.items():
                reviews = analysis.get("reviews", [])
                if isinstance(reviews, list):
                    all_reviews.extend(reviews)

            if all_reviews:
                # 情感分析
                result = visualizer.analyze_reviews(reviews=all_reviews)
                self.sentiment_analysis = result
                logger.info(f"情感分析完成: {len(all_reviews)} 条评论")

                # 生成词云数据
                wordcloud = visualizer.generate_word_cloud(reviews=all_reviews)
                self.sentiment_analysis["wordcloud"] = wordcloud

                # 提取标签
                tags = visualizer.extract_tags(reviews=all_reviews)
                self.sentiment_analysis["tags"] = tags
                logger.info(f"词云和标签提取完成")
            else:
                logger.info("评论列表为空，跳过情感可视化")
        except Exception as e:
            logger.warning(f"情感可视化失败: {e}")

    def _step_supplier_scoring(self):
        """Step 8.5: 供应商评分"""
        logger.info(f"\n--- Step 8.5: 供应商评分 ---")

        try:
            from analysis.supplier_scorer import SupplierScorer
            scorer = SupplierScorer()

            # 收集所有产品的 1688 货源供应商
            all_suppliers = []
            for product in self.products[:5]:
                sources = product.get("sources_1688", [])
                for source in sources:
                    if source not in all_suppliers:
                        all_suppliers.append(source)

            if all_suppliers:
                # 计算市场均价
                prices = [s.get("price", 0) for s in all_suppliers if s.get("price")]
                market_avg = sum(prices) / len(prices) if prices else 0

                # 批量评分
                self.supplier_scores = scorer.score_multiple_suppliers(
                    all_suppliers, market_avg
                )
                logger.info(f"评分了 {len(self.supplier_scores)} 个供应商")

                # 将评分结果关联回产品
                for product in self.products[:5]:
                    sources = product.get("sources_1688", [])
                    for source in sources:
                        for scored in self.supplier_scores:
                            if (scored.get("supplier_name") == source.get("name") or
                                scored.get("supplier_url") == source.get("url")):
                                source["score"] = scored["total_score"]
                                source["grade"] = scored["grade"]
                                break
            else:
                logger.info("无 1688 货源数据，跳过供应商评分")
        except Exception as e:
            logger.warning(f"供应商评分失败: {e}")

    def _step_pricing_optimization(self, keyword: str):
        """Step 9.5: 定价策略优化"""
        logger.info(f"\n--- Step 9.5: 定价策略优化 ---")

        try:
            from analysis.pricing_optimizer import PricingOptimizer
            optimizer = PricingOptimizer(
                marketplace=self.marketplace,
                exchange_rate=self.config.get("exchange_rate", 170.0),  # KRW/CNY
            )

            # 1. 竞品价格分布分析
            distribution = optimizer.analyze_price_distribution(self.products)
            self.pricing_analysis["distribution"] = distribution

            # 2. 如果有利润计算结果，生成定价策略对比
            if self.profit_results:
                # 从利润结果中提取成本参数
                first_profit = self.profit_results[0]

                # 兼容不同利润计算器的输出格式
                costs = first_profit.get("costs", first_profit)
                cost_params = {
                    "sourcing_cost_rmb": (
                        costs.get("cogs_rmb", 0) or
                        costs.get("sourcing_cost_rmb", 0) or
                        costs.get("source_price_rmb", 0)
                    ),
                    "shipping_cost_per_kg": (
                        costs.get("shipping_rmb_per_kg", 0) or
                        costs.get("shipping_cost_per_kg", 0)
                    ),
                    "weight_kg": costs.get("weight_kg", 0.5),
                    "fba_fee": costs.get("fba_fulfillment_fee", 0) or costs.get("platform_fee", 0),
                }

                # 多策略对比
                strategies = optimizer.compare_strategies(cost_params, self.products)
                self.pricing_analysis["strategies"] = strategies

                # 最优定价建议
                optimal = optimizer.suggest_optimal_price(
                    cost_params, self.products, target_margin=0.25
                )
                self.pricing_analysis["optimal"] = optimal

                # 价格弹性模拟
                elasticity = optimizer.simulate_price_elasticity(
                    cost_params, self.products
                )
                self.pricing_analysis["elasticity"] = elasticity

                logger.info(
                    f"推荐策略: {optimal.get('strategy_name', 'N/A')}  "
                    f"最优价格: {optimal.get('optimal_price', 0):.0f}  "
                    f"利润率: {optimal.get('profit_at_optimal', {}).get('margin_pct', 0):.1f}%"
                )
            else:
                logger.info("无利润计算结果，仅生成价格分布分析")
        except Exception as e:
            logger.warning(f"定价策略优化失败: {e}")

    def _step_decision_evaluation(self):
        """Step 9.8: AI 选品决策评估"""
        logger.info(f"\n--- Step 9.8: AI 选品决策评估 ---")

        try:
            from analysis.ai_analysis.product_decision_engine import ProductDecisionEngine
            engine = ProductDecisionEngine(ai_client=self.ai_client)

            result = engine.batch_evaluate(
                products=self.products,
                market_data=self.category_analysis,
                profit_results=self.profit_results,
                competitor_data=self.competitor_analysis,
            )
            self.decision_results = result

            go_count = result.get("summary", {}).get("go_count", 0)
            total = result.get("total_evaluated", 0)
            logger.info(f"AI 决策评估完成: {total} 个产品, {go_count} 个推荐 GO")
        except Exception as e:
            logger.warning(f"AI 决策评估失败: {e}")

    # ============================================================
    # 增强报告追加
    # ============================================================

    def _append_enhanced_report(self, report_path: str, keyword: str):
        """将增强模块的分析结果追加到报告中"""
        if not report_path or not os.path.isfile(report_path):
            return

        try:
            sections = []

            # 关键词研究部分
            if self.keyword_analysis:
                sections.append(self._format_keyword_section())

            # 竞品分析部分
            if self.competitor_analysis:
                sections.append(self._format_competitor_section())

            # 情感分析部分
            if self.sentiment_analysis:
                sections.append(self._format_sentiment_section())

            # 供应商评分部分
            if self.supplier_scores:
                sections.append(self._format_supplier_section())

            # 定价策略部分
            if self.pricing_analysis:
                sections.append(self._format_pricing_section())

            # AI 决策部分
            if self.decision_results:
                sections.append(self._format_decision_section())

            if sections:
                with open(report_path, "a", encoding="utf-8") as f:
                    f.write("\n\n---\n\n")
                    f.write("## 增强分析模块\n\n")
                    f.write("\n\n".join(sections))

                logger.info(f"增强分析数据已追加到报告: {len(sections)} 个模块")
        except Exception as e:
            logger.warning(f"追加增强报告失败: {e}")

    def _format_keyword_section(self) -> str:
        """格式化关键词研究报告段落"""
        lines = ["### 关键词研究\n"]

        difficulty = self.keyword_analysis.get("difficulty", {})
        volume = self.keyword_analysis.get("search_volume", {})
        long_tail = self.keyword_analysis.get("long_tail", [])

        lines.append(f"- **竞争难度**: {difficulty.get('difficulty_score', 'N/A')}/100 "
                     f"({difficulty.get('difficulty_level', 'N/A')})")
        lines.append(f"- **估算月搜索量**: {volume.get('estimated_monthly_searches', 'N/A')}")
        lines.append(f"- **长尾关键词数**: {len(long_tail)} 个")

        if long_tail[:5]:
            lines.append("\n**推荐长尾词:**\n")
            for kw in long_tail[:5]:
                if isinstance(kw, dict):
                    lines.append(f"  - {kw.get('keyword', kw)}")
                else:
                    lines.append(f"  - {kw}")

        return "\n".join(lines)

    def _format_competitor_section(self) -> str:
        """格式化竞品分析报告段落"""
        lines = ["### 竞争格局分析\n"]

        concentration = self.competitor_analysis.get("market_concentration", {})
        lines.append(f"- **市场集中度 (HHI)**: {concentration.get('hhi', 'N/A')}")
        lines.append(f"- **集中度等级**: {concentration.get('level', 'N/A')}")

        price_bands = self.competitor_analysis.get("price_bands", [])
        if price_bands:
            lines.append("\n**价格带分布:**\n")
            lines.append("| 价格带 | 产品数 | 占比 |")
            lines.append("|--------|--------|------|")
            for band in price_bands[:5]:
                lines.append(
                    f"| {band.get('range', 'N/A')} | "
                    f"{band.get('count', 0)} | "
                    f"{band.get('percentage', 0):.1f}% |"
                )

        gaps = self.competitor_analysis.get("market_gaps", {}).get("gaps", [])
        if gaps:
            lines.append(f"\n**市场空白**: 发现 {len(gaps)} 个潜在机会点")
            for gap in gaps[:3]:
                lines.append(f"  - {gap.get('description', gap)}")

        return "\n".join(lines)

    def _format_sentiment_section(self) -> str:
        """格式化情感分析报告段落"""
        lines = ["### 评论情感分析\n"]

        overall = self.sentiment_analysis.get("overall", {})
        lines.append(f"- **正面评论占比**: {overall.get('positive_pct', 0):.1f}%")
        lines.append(f"- **负面评论占比**: {overall.get('negative_pct', 0):.1f}%")
        lines.append(f"- **中性评论占比**: {overall.get('neutral_pct', 0):.1f}%")

        tags = self.sentiment_analysis.get("tags", [])
        if tags:
            pos_tags = [t for t in tags if t.get("sentiment") == "positive"][:5]
            neg_tags = [t for t in tags if t.get("sentiment") == "negative"][:5]

            if pos_tags:
                lines.append("\n**高频正面标签:** " +
                           ", ".join(t.get("tag", "") for t in pos_tags))
            if neg_tags:
                lines.append("**高频负面标签:** " +
                           ", ".join(t.get("tag", "") for t in neg_tags))

        return "\n".join(lines)

    def _format_supplier_section(self) -> str:
        """格式化供应商评分报告段落"""
        lines = ["### 供应商评分\n"]

        lines.append("| 供应商 | 综合评分 | 等级 | 信誉 | 产品力 | 服务 | 价格 |")
        lines.append("|--------|----------|------|------|--------|------|------|")

        def _dim_score(val):
            """从维度值中提取分数（兼容 dict 和 number）"""
            if isinstance(val, dict):
                return val.get("score", 0)
            return val if isinstance(val, (int, float)) else 0

        for s in sorted(self.supplier_scores, key=lambda x: x.get("total_score", 0), reverse=True)[:5]:
            dims = s.get("dimensions", {})
            lines.append(
                f"| {s.get('supplier_name', 'N/A')[:15]} | "
                f"{s.get('total_score', 0):.1f} | "
                f"{s.get('grade', 'N/A')} | "
                f"{_dim_score(dims.get('credibility', 0)):.0f} | "
                f"{_dim_score(dims.get('product_capability', 0)):.0f} | "
                f"{_dim_score(dims.get('service_quality', 0)):.0f} | "
                f"{_dim_score(dims.get('price_competitiveness', 0)):.0f} |"
            )

        return "\n".join(lines)

    def _format_pricing_section(self) -> str:
        """格式化定价策略报告段落"""
        lines = ["### 定价策略建议\n"]

        distribution = self.pricing_analysis.get("distribution", {})
        lines.append(f"- **市场均价**: {distribution.get('mean_price', 0):.0f}")
        lines.append(f"- **中位数价格**: {distribution.get('median_price', 0):.0f}")
        lines.append(f"- **价格范围**: {distribution.get('min_price', 0):.0f} - "
                     f"{distribution.get('max_price', 0):.0f}")

        optimal = self.pricing_analysis.get("optimal", {})
        if optimal:
            lines.append(f"\n**推荐策略**: {optimal.get('strategy_name', 'N/A')}")
            lines.append(f"- **最优价格**: {optimal.get('optimal_price', 0):.0f}")
            profit_info = optimal.get("profit_at_optimal", {})
            lines.append(f"- **预期利润率**: {profit_info.get('margin_pct', 0):.1f}%")

        strategies = self.pricing_analysis.get("strategies", [])
        if strategies:
            lines.append("\n**策略对比:**\n")
            lines.append("| 策略 | 建议价格 | 利润率 | 适用场景 |")
            lines.append("|------|----------|--------|----------|")
            for st in strategies[:4]:
                lines.append(
                    f"| {st.get('name', 'N/A')} | "
                    f"{st.get('suggested_price', 0):.0f} | "
                    f"{st.get('margin_pct', 0):.1f}% | "
                    f"{st.get('suitable_for', 'N/A')[:25]} |"
                )

        return "\n".join(lines)

    def _format_decision_section(self) -> str:
        """格式化 AI 决策报告段落"""
        lines = ["### AI 选品决策\n"]

        summary = self.decision_results.get("summary", {})
        lines.append(f"- **评估产品数**: {self.decision_results.get('total_evaluated', 0)}")
        lines.append(f"- **推荐 GO**: {summary.get('go_count', 0)} 个")
        lines.append(f"- **推荐 NO-GO**: {summary.get('nogo_count', 0)} 个")
        lines.append(f"- **待观察**: {summary.get('watch_count', 0)} 个")

        evaluations = self.decision_results.get("evaluations", [])
        go_products = [e for e in evaluations if e.get("decision") == "GO"]
        if go_products:
            lines.append("\n**推荐选品 (GO):**\n")
            lines.append("| 产品 | 综合评分 | 决策 | 核心理由 |")
            lines.append("|------|----------|------|----------|")
            for p in go_products[:5]:
                lines.append(
                    f"| {p.get('title', 'N/A')[:20]} | "
                    f"{p.get('total_score', 0):.0f}/100 | "
                    f"**GO** | "
                    f"{p.get('primary_reason', 'N/A')[:30]} |"
                )

        return "\n".join(lines)

    # ============================================================
    # 数据保存
    # ============================================================

    def save_raw_data(self, keyword: str, output_dir: str = "data"):
        """保存原始数据到JSON文件（含增强模块数据）"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        data = {
            "platform": self.platform,
            "marketplace": self.marketplace,
            "keyword": keyword,
            "timestamp": timestamp,
            # 核心数据
            "products": self.products,
            "daily_stats": self.daily_stats,
            "review_analyses": self.review_analyses,
            "detail_analyses": self.detail_analyses,
            "category_analysis": self.category_analysis,
            "profit_results": self.profit_results,
            # 增强模块数据
            "keyword_analysis": self.keyword_analysis,
            "bsr_tracking": self.bsr_tracking,
            "competitor_analysis": self.competitor_analysis,
            "sentiment_analysis": self.sentiment_analysis,
            "supplier_scores": self.supplier_scores,
            "pricing_analysis": self.pricing_analysis,
            "decision_results": self.decision_results,
        }

        filepath = os.path.join(output_dir, f"raw_{keyword}_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Raw data saved to: {filepath}")
        return filepath
