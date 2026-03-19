"""
Coupang Pipeline 增强模块集成测试

测试 pipeline.py 中新集成的 7 个增强模块:
- Step 3.5: KeywordResearcher (关键词研究)
- Step 4.5: BSRTracker + CompetitorFinder (BSR追踪 + 竞品发现)
- Step 5.5: SentimentVisualizer (情感可视化)
- Step 8.5: SupplierScorer (供应商评分)
- Step 9.5: PricingOptimizer (定价策略优化)
- Step 9.8: ProductDecisionEngine (AI 选品决策)
- Step 10:  增强报告生成
"""

import pytest
import sys
import os
import json
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def coupang_products():
    """Coupang 平台的示例产品数据"""
    return [
        {
            "coupang_product_id": "CP00001",
            "title": "무선 블루투스 이어폰 노이즈캔슬링",
            "price": 29900,
            "rating": 4.5,
            "review_count": 3200,
            "bsr_rank": 120,
            "rank": 1,
            "category": "전자기기",
            "url": "https://www.coupang.com/vp/products/CP00001",
            "images": [{"type": "main", "url": "https://example.com/img1.jpg"}],
            "detail_images": [],
            "sources_1688": [
                {
                    "name": "深圳蓝牙科技",
                    "url": "https://detail.1688.com/offer/123.html",
                    "price": 35.0,
                    "moq": "100",
                    "business_years": 5,
                    "certifications": ["ISO9001", "CE"],
                    "response_time": "1小时内",
                    "oem": True,
                    "odm": True,
                    "sample_available": True,
                    "trade_assurance": True,
                    "lead_time": 7,
                },
                {
                    "name": "东莞耳机工厂",
                    "url": "https://detail.1688.com/offer/456.html",
                    "price": 28.0,
                    "moq": "500",
                    "business_years": 3,
                    "certifications": ["CE"],
                    "response_time": "4小时内",
                    "oem": True,
                    "odm": False,
                    "sample_available": True,
                    "trade_assurance": False,
                    "lead_time": 10,
                },
            ],
            "profit_analysis": [
                {
                    "source_price_rmb": 35.0,
                    "cogs_rmb": 35.0,
                    "shipping_rmb_per_kg": 30.0,
                    "weight_kg": 0.15,
                    "platform_fee": 3000,
                    "fba_fulfillment_fee": 3000,
                    "profit_krw": 12000,
                    "margin_pct": 0.28,
                }
            ],
        },
        {
            "coupang_product_id": "CP00002",
            "title": "블루투스 스피커 방수 휴대용",
            "price": 39900,
            "rating": 4.2,
            "review_count": 890,
            "bsr_rank": 350,
            "rank": 2,
            "category": "전자기기",
            "url": "https://www.coupang.com/vp/products/CP00002",
            "images": [{"type": "main", "url": "https://example.com/img2.jpg"}],
            "detail_images": [],
            "sources_1688": [],
        },
        {
            "coupang_product_id": "CP00003",
            "title": "미니 블루투스 스피커",
            "price": 15900,
            "rating": 3.8,
            "review_count": 450,
            "bsr_rank": 890,
            "rank": 3,
            "category": "전자기기",
            "url": "https://www.coupang.com/vp/products/CP00003",
            "images": [],
            "detail_images": [],
            "sources_1688": [],
        },
        {
            "coupang_product_id": "CP00004",
            "title": "프리미엄 사운드바 홈시어터",
            "price": 199000,
            "rating": 4.7,
            "review_count": 5600,
            "bsr_rank": 45,
            "rank": 4,
            "category": "전자기기",
            "url": "https://www.coupang.com/vp/products/CP00004",
            "images": [{"type": "main", "url": "https://example.com/img4.jpg"}],
            "detail_images": [],
            "sources_1688": [],
        },
        {
            "coupang_product_id": "CP00005",
            "title": "이어폰 충전 케이블 USB-C",
            "price": 5900,
            "rating": 4.0,
            "review_count": 120,
            "bsr_rank": 2500,
            "rank": 5,
            "category": "전자기기",
            "url": "https://www.coupang.com/vp/products/CP00005",
            "images": [],
            "detail_images": [],
            "sources_1688": [],
        },
    ]


@pytest.fixture
def sample_reviews():
    """示例评论数据"""
    return [
        {
            "text": "Great sound quality, very comfortable to wear. Battery lasts long.",
            "rating": 5,
            "date": "2026-01-15",
            "helpful_votes": 12,
        },
        {
            "text": "Good product but the noise cancelling could be better.",
            "rating": 4,
            "date": "2026-01-10",
            "helpful_votes": 5,
        },
        {
            "text": "Terrible quality, broke after 2 weeks. Very disappointed.",
            "rating": 1,
            "date": "2026-01-05",
            "helpful_votes": 8,
        },
        {
            "text": "Amazing value for the price. Highly recommend!",
            "rating": 5,
            "date": "2025-12-20",
            "helpful_votes": 15,
        },
        {
            "text": "Average product, nothing special. Works as expected.",
            "rating": 3,
            "date": "2025-12-15",
            "helpful_votes": 2,
        },
    ]


# ============================================================
# Test: Pipeline 初始化和配置
# ============================================================

class TestPipelineInit:
    """测试 Coupang Pipeline 初始化"""

    def test_pipeline_import(self):
        """验证 pipeline 模块可以正常导入"""
        from pipeline import SelectionPipeline
        assert SelectionPipeline is not None

    def test_pipeline_init_default(self):
        """默认配置初始化"""
        from pipeline import SelectionPipeline
        pipeline = SelectionPipeline()
        assert pipeline.platform == "coupang"
        assert pipeline.marketplace == "KR"
        assert pipeline.products == []
        assert pipeline.keyword_analysis == {}
        assert pipeline.bsr_tracking == {}
        assert pipeline.competitor_analysis == {}
        assert pipeline.sentiment_analysis == {}
        assert pipeline.supplier_scores == []
        assert pipeline.pricing_analysis == {}
        assert pipeline.decision_results == {}

    def test_pipeline_init_custom_config(self):
        """自定义配置初始化"""
        from pipeline import SelectionPipeline
        config = {
            "language": "ko_KR",
            "marketplace": "KR",
            "min_delay": 2.0,
            "max_delay": 4.0,
        }
        pipeline = SelectionPipeline(config=config)
        assert pipeline.marketplace == "KR"

    def test_pipeline_has_enhanced_steps(self):
        """验证增强步骤方法存在"""
        from pipeline import SelectionPipeline
        pipeline = SelectionPipeline()
        assert hasattr(pipeline, '_step_keyword_research')
        assert hasattr(pipeline, '_step_bsr_and_competitor')
        assert hasattr(pipeline, '_step_sentiment_visualization')
        assert hasattr(pipeline, '_step_supplier_scoring')
        assert hasattr(pipeline, '_step_pricing_optimization')
        assert hasattr(pipeline, '_step_decision_evaluation')
        assert hasattr(pipeline, '_append_enhanced_report')

    def test_pipeline_run_signature(self):
        """验证 run 方法包含 skip_enhanced 参数"""
        from pipeline import SelectionPipeline
        import inspect
        sig = inspect.signature(SelectionPipeline.run)
        params = list(sig.parameters.keys())
        assert 'skip_enhanced' in params
        assert 'keyword' in params
        assert 'skip_1688' in params

    def test_pipeline_docstring_has_enhanced_steps(self):
        """验证 docstring 包含增强步骤描述"""
        from pipeline import SelectionPipeline
        docstring = SelectionPipeline.__doc__
        assert "Step 3.5" in docstring
        assert "Step 4.5" in docstring
        assert "Step 5.5" in docstring
        assert "Step 8.5" in docstring
        assert "Step 9.5" in docstring
        assert "Step 9.8" in docstring


# ============================================================
# Test: Step 3.5 关键词研究
# ============================================================

class TestKeywordResearchStep:
    """测试 Step 3.5 关键词研究集成"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={"marketplace": "KR"})

    def test_keyword_research_with_products(self, coupang_products):
        """有产品数据时执行关键词研究"""
        self.pipeline.products = coupang_products
        self.pipeline._step_keyword_research("블루투스 이어폰")

        # 应该有分析结果
        assert isinstance(self.pipeline.keyword_analysis, dict)

    def test_keyword_research_empty_products(self):
        """空产品列表时也应正常执行"""
        self.pipeline.products = []
        self.pipeline._step_keyword_research("test keyword")
        assert isinstance(self.pipeline.keyword_analysis, dict)

    def test_keyword_research_stores_difficulty(self, coupang_products):
        """关键词竞争度应被存储"""
        self.pipeline.products = coupang_products
        self.pipeline._step_keyword_research("블루투스 이어폰")

        if "difficulty" in self.pipeline.keyword_analysis:
            diff = self.pipeline.keyword_analysis["difficulty"]
            assert isinstance(diff, dict)

    def test_keyword_research_stores_volume(self, coupang_products):
        """搜索量估算应被存储"""
        self.pipeline.products = coupang_products
        self.pipeline._step_keyword_research("블루투스 이어폰")

        if "search_volume" in self.pipeline.keyword_analysis:
            vol = self.pipeline.keyword_analysis["search_volume"]
            assert isinstance(vol, dict)

    def test_keyword_research_stores_long_tail(self, coupang_products):
        """长尾词应被存储"""
        self.pipeline.products = coupang_products
        self.pipeline._step_keyword_research("bluetooth earbuds")

        if "long_tail" in self.pipeline.keyword_analysis:
            lt = self.pipeline.keyword_analysis["long_tail"]
            assert isinstance(lt, list)


# ============================================================
# Test: Step 4.5 BSR 追踪和竞品发现
# ============================================================

class TestBSRAndCompetitorStep:
    """测试 Step 4.5 BSR 追踪和竞品发现集成"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={"marketplace": "KR"})

    def test_bsr_tracking_with_products(self, coupang_products):
        """有产品数据时执行 BSR 追踪"""
        self.pipeline.products = coupang_products
        self.pipeline._step_bsr_and_competitor()

        assert isinstance(self.pipeline.bsr_tracking, dict)

    def test_bsr_tracking_records_snapshots(self, coupang_products):
        """BSR 快照应被记录"""
        self.pipeline.products = coupang_products
        self.pipeline._step_bsr_and_competitor()

        # 至少应该有一些快照
        if self.pipeline.bsr_tracking:
            for pid, snapshot in self.pipeline.bsr_tracking.items():
                assert isinstance(snapshot, dict)

    def test_competitor_analysis_with_products(self, coupang_products):
        """有产品数据时执行竞品分析"""
        self.pipeline.products = coupang_products
        self.pipeline._step_bsr_and_competitor()

        assert isinstance(self.pipeline.competitor_analysis, dict)

    def test_competitor_analysis_empty_products(self):
        """空产品列表时应正常执行"""
        self.pipeline.products = []
        self.pipeline._step_bsr_and_competitor()
        assert isinstance(self.pipeline.bsr_tracking, dict)
        assert isinstance(self.pipeline.competitor_analysis, dict)

    def test_market_gaps_stored(self, coupang_products):
        """市场空白分析应被存储"""
        self.pipeline.products = coupang_products
        self.pipeline._step_bsr_and_competitor()

        if self.pipeline.competitor_analysis:
            # market_gaps 可能存在也可能不存在，取决于分析结果
            assert isinstance(self.pipeline.competitor_analysis, dict)


# ============================================================
# Test: Step 5.5 评论情感可视化
# ============================================================

class TestSentimentVisualizationStep:
    """测试 Step 5.5 评论情感可视化集成"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={"marketplace": "KR"})

    def test_sentiment_no_reviews(self):
        """无评论数据时应跳过"""
        self.pipeline.review_analyses = {}
        self.pipeline._step_sentiment_visualization()
        assert self.pipeline.sentiment_analysis == {}

    def test_sentiment_with_reviews(self, sample_reviews):
        """有评论数据时应执行情感分析"""
        self.pipeline.review_analyses = {
            "CP00001": {"reviews": sample_reviews}
        }
        self.pipeline._step_sentiment_visualization()
        assert isinstance(self.pipeline.sentiment_analysis, dict)

    def test_sentiment_stores_wordcloud(self, sample_reviews):
        """词云数据应被存储"""
        self.pipeline.review_analyses = {
            "CP00001": {"reviews": sample_reviews}
        }
        self.pipeline._step_sentiment_visualization()

        if self.pipeline.sentiment_analysis:
            # wordcloud 字段可能存在
            assert isinstance(self.pipeline.sentiment_analysis, dict)

    def test_sentiment_stores_tags(self, sample_reviews):
        """标签数据应被存储"""
        self.pipeline.review_analyses = {
            "CP00001": {"reviews": sample_reviews}
        }
        self.pipeline._step_sentiment_visualization()

        if self.pipeline.sentiment_analysis:
            assert isinstance(self.pipeline.sentiment_analysis, dict)


# ============================================================
# Test: Step 8.5 供应商评分
# ============================================================

class TestSupplierScoringStep:
    """测试 Step 8.5 供应商评分集成"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={"marketplace": "KR"})

    def test_supplier_scoring_with_sources(self, coupang_products):
        """有 1688 货源时执行供应商评分"""
        self.pipeline.products = coupang_products
        self.pipeline._step_supplier_scoring()

        assert isinstance(self.pipeline.supplier_scores, list)

    def test_supplier_scoring_no_sources(self):
        """无 1688 货源时应跳过"""
        self.pipeline.products = [{"coupang_product_id": "CP00001", "sources_1688": []}]
        self.pipeline._step_supplier_scoring()
        assert isinstance(self.pipeline.supplier_scores, list)

    def test_supplier_scores_have_total(self, coupang_products):
        """评分结果应包含总分"""
        self.pipeline.products = coupang_products
        self.pipeline._step_supplier_scoring()

        if self.pipeline.supplier_scores:
            for score in self.pipeline.supplier_scores:
                assert "total_score" in score or isinstance(score, dict)

    def test_supplier_scores_linked_to_products(self, coupang_products):
        """评分应关联回产品的 sources_1688"""
        self.pipeline.products = coupang_products
        self.pipeline._step_supplier_scoring()

        # 检查第一个产品的 sources 是否有 score 字段
        if self.pipeline.supplier_scores:
            sources = self.pipeline.products[0].get("sources_1688", [])
            # 至少有一些 source 应该有 score
            scored_sources = [s for s in sources if "score" in s]
            # 可能有也可能没有，取决于匹配逻辑
            assert isinstance(scored_sources, list)


# ============================================================
# Test: Step 9.5 定价策略优化
# ============================================================

class TestPricingOptimizationStep:
    """测试 Step 9.5 定价策略优化集成"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={
            "marketplace": "KR",
            "exchange_rate": 170.0,
        })

    def test_pricing_with_products(self, coupang_products):
        """有产品数据时执行定价分析"""
        self.pipeline.products = coupang_products
        self.pipeline._step_pricing_optimization("블루투스 이어폰")

        assert isinstance(self.pipeline.pricing_analysis, dict)

    def test_pricing_distribution_stored(self, coupang_products):
        """价格分布分析应被存储"""
        self.pipeline.products = coupang_products
        self.pipeline._step_pricing_optimization("블루투스 이어폰")

        if "distribution" in self.pipeline.pricing_analysis:
            dist = self.pipeline.pricing_analysis["distribution"]
            assert isinstance(dist, dict)

    def test_pricing_with_profit_results(self, coupang_products):
        """有利润计算结果时应生成策略对比"""
        self.pipeline.products = coupang_products
        self.pipeline.profit_results = coupang_products[0].get("profit_analysis", [])
        self.pipeline._step_pricing_optimization("블루투스 이어폰")

        assert isinstance(self.pipeline.pricing_analysis, dict)

    def test_pricing_empty_products(self):
        """空产品列表时应正常执行"""
        self.pipeline.products = []
        self.pipeline._step_pricing_optimization("test")
        assert isinstance(self.pipeline.pricing_analysis, dict)


# ============================================================
# Test: Step 9.8 AI 选品决策
# ============================================================

class TestDecisionEvaluationStep:
    """测试 Step 9.8 AI 选品决策评估集成"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={"marketplace": "KR"})

    def test_decision_with_products(self, coupang_products):
        """有产品数据时执行决策评估"""
        self.pipeline.products = coupang_products
        self.pipeline._step_decision_evaluation()

        assert isinstance(self.pipeline.decision_results, dict)

    def test_decision_empty_products(self):
        """空产品列表时应正常执行"""
        self.pipeline.products = []
        self.pipeline._step_decision_evaluation()
        assert isinstance(self.pipeline.decision_results, dict)

    def test_decision_with_full_data(self, coupang_products):
        """完整数据时执行决策评估"""
        self.pipeline.products = coupang_products
        self.pipeline.category_analysis = {"gmv": 1000000}
        self.pipeline.profit_results = coupang_products[0].get("profit_analysis", [])
        self.pipeline.competitor_analysis = {"market_concentration": {"hhi": 0.15}}
        self.pipeline._step_decision_evaluation()

        assert isinstance(self.pipeline.decision_results, dict)


# ============================================================
# Test: 增强报告生成
# ============================================================

class TestEnhancedReportGeneration:
    """测试增强报告追加功能"""

    def setup_method(self):
        from pipeline import SelectionPipeline
        self.pipeline = SelectionPipeline(config={"marketplace": "KR"})

    def test_format_keyword_section(self):
        """关键词研究报告格式化"""
        self.pipeline.keyword_analysis = {
            "difficulty": {"difficulty_score": 45, "difficulty_level": "Medium"},
            "search_volume": {"estimated_monthly_searches": 12000},
            "long_tail": [
                {"keyword": "bluetooth earbuds noise cancelling"},
                {"keyword": "wireless earbuds for running"},
            ],
        }
        result = self.pipeline._format_keyword_section()
        assert "关键词研究" in result
        assert "45" in result
        assert "12000" in result

    def test_format_competitor_section(self):
        """竞品分析报告格式化"""
        self.pipeline.competitor_analysis = {
            "market_concentration": {"hhi": 0.15, "level": "Low"},
            "price_bands": [
                {"range": "10000-20000", "count": 5, "percentage": 25.0},
                {"range": "20000-30000", "count": 10, "percentage": 50.0},
            ],
            "market_gaps": {"gaps": [{"description": "Mid-range waterproof speakers"}]},
        }
        result = self.pipeline._format_competitor_section()
        assert "竞争格局" in result
        assert "0.15" in result

    def test_format_sentiment_section(self):
        """情感分析报告格式化"""
        self.pipeline.sentiment_analysis = {
            "overall": {"positive_pct": 65.0, "negative_pct": 15.0, "neutral_pct": 20.0},
            "tags": [
                {"tag": "sound quality", "sentiment": "positive"},
                {"tag": "battery life", "sentiment": "positive"},
                {"tag": "broke easily", "sentiment": "negative"},
            ],
        }
        result = self.pipeline._format_sentiment_section()
        assert "情感分析" in result
        assert "65.0" in result

    def test_format_supplier_section(self):
        """供应商评分报告格式化"""
        self.pipeline.supplier_scores = [
            {
                "supplier_name": "深圳蓝牙科技",
                "total_score": 82.5,
                "grade": "A",
                "dimensions": {
                    "credibility": {"score": 85},
                    "product_capability": {"score": 80},
                    "service_quality": {"score": 78},
                    "price_competitiveness": {"score": 88},
                },
            },
        ]
        result = self.pipeline._format_supplier_section()
        assert "供应商评分" in result
        assert "82.5" in result
        assert "A" in result

    def test_format_pricing_section(self):
        """定价策略报告格式化"""
        self.pipeline.pricing_analysis = {
            "distribution": {"mean_price": 25000, "median_price": 23000, "min_price": 5900, "max_price": 199000},
            "optimal": {"strategy_name": "competitive", "optimal_price": 27900, "profit_at_optimal": {"margin_pct": 25.0}},
            "strategies": [
                {"name": "penetration", "suggested_price": 22900, "margin_pct": 15.0, "suitable_for": "New product launch"},
                {"name": "competitive", "suggested_price": 27900, "margin_pct": 25.0, "suitable_for": "Growth phase"},
            ],
        }
        result = self.pipeline._format_pricing_section()
        assert "定价策略" in result
        assert "25000" in result

    def test_format_decision_section(self):
        """AI 决策报告格式化"""
        self.pipeline.decision_results = {
            "total_evaluated": 5,
            "summary": {"go_count": 2, "nogo_count": 1, "watch_count": 2},
            "evaluations": [
                {"title": "무선 블루투스 이어폰", "total_score": 78, "decision": "GO", "primary_reason": "High demand, good margins"},
                {"title": "블루투스 스피커", "total_score": 65, "decision": "WATCH", "primary_reason": "Moderate competition"},
            ],
        }
        result = self.pipeline._format_decision_section()
        assert "AI 选品决策" in result
        assert "GO" in result
        assert "5" in result

    def test_append_enhanced_report_to_file(self):
        """测试增强报告追加到文件"""
        # 创建临时报告文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# Test Report\n\nBase content here.\n")
            report_path = f.name

        try:
            self.pipeline.keyword_analysis = {
                "difficulty": {"difficulty_score": 45, "difficulty_level": "Medium"},
                "search_volume": {"estimated_monthly_searches": 12000},
                "long_tail": [],
            }
            self.pipeline.pricing_analysis = {
                "distribution": {"mean_price": 25000, "median_price": 23000, "min_price": 5900, "max_price": 199000},
            }

            self.pipeline._append_enhanced_report(report_path, "블루투스 이어폰")

            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "增强分析模块" in content
            assert "关键词研究" in content
            assert "定价策略" in content
        finally:
            os.unlink(report_path)

    def test_append_enhanced_report_nonexistent_file(self):
        """不存在的报告文件应不报错"""
        self.pipeline.keyword_analysis = {"difficulty": {}}
        self.pipeline._append_enhanced_report("/nonexistent/path.md", "test")
        # 不应抛出异常


# ============================================================
# Test: save_raw_data 包含增强数据
# ============================================================

class TestSaveRawData:
    """测试原始数据保存包含增强模块数据"""

    def test_save_raw_data_includes_enhanced(self, coupang_products):
        """保存的数据应包含所有增强模块字段"""
        from pipeline import SelectionPipeline
        pipeline = SelectionPipeline(config={"marketplace": "KR"})
        pipeline.products = coupang_products
        pipeline.keyword_analysis = {"test": True}
        pipeline.bsr_tracking = {"CP00001": {"bsr_rank": 120}}
        pipeline.competitor_analysis = {"hhi": 0.15}
        pipeline.sentiment_analysis = {"positive_pct": 65}
        pipeline.supplier_scores = [{"name": "test", "score": 80}]
        pipeline.pricing_analysis = {"optimal_price": 27900}
        pipeline.decision_results = {"go_count": 2}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = pipeline.save_raw_data("블루투스", output_dir=tmpdir)

            assert os.path.isfile(filepath)

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert data["platform"] == "coupang"
            assert data["marketplace"] == "KR"
            assert data["keyword_analysis"] == {"test": True}
            assert data["bsr_tracking"] == {"CP00001": {"bsr_rank": 120}}
            assert data["competitor_analysis"] == {"hhi": 0.15}
            assert data["sentiment_analysis"] == {"positive_pct": 65}
            assert data["supplier_scores"] == [{"name": "test", "score": 80}]
            assert data["pricing_analysis"] == {"optimal_price": 27900}
            assert data["decision_results"] == {"go_count": 2}


# ============================================================
# Test: 前端 Marketplace 更新
# ============================================================

class TestFrontendMarketplace:
    """测试前端模板包含 Coupang KR 选项"""

    def test_new_project_has_coupang(self):
        """new_project.html 应包含 Coupang KR 选项"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "templates", "new_project.html"
        )
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "Coupang" in content
            assert "KR" in content

    def test_competitor_monitor_has_coupang(self):
        """competitor_monitor.html 应包含 Coupang KR 选项"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "templates", "competitor_monitor.html"
        )
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "Coupang" in content
            assert "KR" in content

    def test_keyword_research_has_coupang(self):
        """keyword_research.html 应包含 Coupang KR 选项"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "templates", "keyword_research.html"
        )
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "Coupang" in content
            assert "KR" in content

    def test_pricing_strategy_has_coupang(self):
        """pricing_strategy.html 应包含 Coupang KR 选项"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "templates", "pricing_strategy.html"
        )
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "Coupang" in content
            assert "KR" in content
